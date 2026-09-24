# Bronze → Silver contract (for the Spark ETL)

How the Spark ETL reads Bronze and writes Silver. The Python reference implementation
is `pgs_db.repositories.SilverRepository`; `tests/test_silver.py` proves every rule
below against a real PostgreSQL, using payloads in the `ETL/spark/README.md` §5.2 shape.

Schema version: Alembic revision `e529ca38e6ae`.

```text
crawled_documents  (Bronze, one row per fetched version of a URL)
        │  N:1 -- every version of a URL lands on one page;
        │         pages.crawled_document_id points at the newest
        ▼
      pages        (Silver, one row per canonical_url)
        │
 ┌──────┴────────┐
 ▼               ▼
page_geo_tags   page_contacts
```

---

## 1. Source of truth, and what is still unsettled

Every Silver field traces to one of two places:

- **`ETL/spark/README.md` §5.2** — the ETL team's own documented output payload.
- **`search-engine/src/pgs_search/models/document.py`** — `SearchDocument` /
  `GeoLocation`, the search team's real consuming code.

The exceptions are the geo-tag provenance fields (`method`, `confidence`,
`mention_text`), which §5.2 does not have yet — see §9.

**No Spark transform exists yet**: `ETL/spark/test_spark.py` is a PySpark hello-world,
and the Airflow DAG is labelled "dummy ... Spark will do this for real later". This
contract encodes the *documented* output, not observed output.

## 2. What is stored, and what is not

**`body_text` is stored.** Silver keeps the page's clean full text (§5.2
`searchable_text`) in `pages.body_text`, with its `word_count`. OpenSearch is built
*from* Silver, so re-indexing, re-ranking or re-tagging never needs Spark to run again
or Bronze to be re-parsed.

**Geography names are not stored.** `geo_location.*_name_en` / `*_name_ne` /
`municipality_type` would duplicate 837 gazetteer rows onto every page and drift.
Tags store codes; `GeoLocationOut.from_tag()` rebuilds the §5.2 block by joining.

---

## 3. Payload → column mapping

`save_page(payload, crawled_document_id=..., domain_id=..., content_hash=..., sim_hash=...)`.
Keyword arguments win over the payload for `content_hash` and `sim_hash`.

### `pages`

| Payload field (§5.2) | Column | Type | Rule |
|---|---|---|---|
| `source_url` (or `canonical_url`) | `canonical_url` | `TEXT` **UNIQUE** | required; the page's identity |
| `searchable_text` (or `body_text`) | `body_text` | `TEXT` | required, non-blank |
| `word_count` | `word_count` | `INTEGER` | optional; else whitespace token count of `body_text` |
| `language_detected` (or `language`) | `language` | `Language` | `ne`→`NE`, `en`→`EN`, `mixed`→`MIXED`, anything else or absent→`OTHER`. Region subtags are ignored (`en-US`→`EN`). |
| `extracted_metadata.title` | `title` | `TEXT` | optional |
| `extracted_metadata.description` | `description` | `TEXT` | optional |
| `extracted_metadata.keywords` | `keywords` | `TEXT[]` | optional |
| `content_type` | `content_type` | `VARCHAR(32)` | default `web_page` |
| `published_at` | `published_at` | `TIMESTAMPTZ` | optional, RFC 3339; naive = UTC |
| `content_hash` / kwarg | `content_hash` | `VARCHAR(64)` | required (ETL §3 exact dedup) |
| `sim_hash` / kwarg | `sim_hash` | `BIGINT` | optional (ETL §3 fuzzy dedup) |
| — kwarg `crawled_document_id` | `crawled_document_id` | `BIGINT` | FK `crawled_documents.id`, `ON DELETE RESTRICT`, indexed |
| — kwarg `domain_id` | `domain_id` | `BIGINT` | optional FK `domains.id` |
| — | `duplicate_of_id` | `BIGINT` | set by `mark_duplicate_of`; NULL = canonical |
| — | `processing_status` / `processing_error` | | search-indexer state; reset to `UNPROCESSED` / NULL on every save |

`document_id` is gone. The public key for a page is `pages.id` internally and
`canonical_url` externally.

### `page_geo_tags` — from `geo_location` (one object, or a list)

| Payload field | Column | Type | Rule |
|---|---|---|---|
| `province_code` | `province_code` | `VARCHAR(4)` | FK `provinces.code` |
| `district_code` | `district_code` | `VARCHAR(4)` | FK `districts.code` |
| `municipality_id` (or `local_body_code`) | `local_body_code` | `VARCHAR(16)` | FK `local_bodies.code`, e.g. `MUN414` |
| `ward_number` | `ward_number` | `INTEGER` | optional, > 0 |
| `method` | `method` | `GeoTagMethod` | **required**: `GAZETTEER`, `NER`, `DOMAIN`, `GEO_META` (case-insensitive) |
| `confidence` | `confidence` | `DOUBLE PRECISION` | **required**, 0–1 inclusive |
| `mention_text` | `mention_text` | `TEXT` | optional; the span that produced the tag |

At least one of the three geo levels must be set (`ck_page_geo_tags_at_least_one_level`).
A block with none is **skipped**, not rejected — most pages are not about a place — and
is not asked for a `method` or `confidence`. A block that *does* resolve a level but
lacks `method`/`confidence` is **rejected**: there is no default, because an invented
confidence would silently skew ranking.

Unique on `(page_id, province_code, district_code, local_body_code, ward_number)` with
`NULLS NOT DISTINCT` (PostgreSQL 15+). Note §5.2's example puts Kaski at `D39`; the
seeded gazetteer has Kaski at **`D38`** (`D39` is Lamjung).

### `page_contacts` — from `extracted_metadata`

| Payload field | `type` | `value` |
|---|---|---|
| `contact_info.emails[]` | `EMAIL` | the address |
| `contact_info.phones[]` | `PHONE` | the number |
| `contact_info.social_links[]` or `social_links[]` | `SOCIAL` | the URL |

Unique on `(page_id, type, value)`; a value repeated on one page is stored once.

---

## 4. The claim → save → mark loop

Bronze's `crawled_documents.processing_status` is the ETL's work queue:

```text
UNPROCESSED ──claim_bronze──▶ PROCESSING ──mark_bronze_processed──▶ PROCESSED
     ▲                            │
     └────── release_stale ───────┤
                                  └──mark_bronze_failed──▶ FAILED (+ processing_error)
```

```python
from datetime import timedelta

from pgs_db import SilverRepository, make_session_factory

Session = make_session_factory()  # expire_on_commit=False: claimed rows stay usable


def run_batch(transform, limit: int = 100) -> None:
    """transform(crawled_document) -> §5.2 payload dict. Raises on bad input."""
    # 1. Claim. Commit at once, so the claim is durable and the row locks are released.
    with Session() as s, s.begin():
        claimed = SilverRepository(s).claim_bronze(limit)

    for doc in claimed:
        try:
            # 2. Save + mark in ONE transaction: the page and the PROCESSED flag
            #    land together or not at all.
            with Session() as s, s.begin():
                repo = SilverRepository(s)
                repo.save_page(
                    transform(doc),
                    crawled_document_id=doc.id,
                    domain_id=doc.domain_id,
                    content_hash=doc.content_hash,
                    sim_hash=doc.sim_hash,
                )
                repo.mark_bronze_processed([doc.id])
        except Exception as exc:
            # 3. Park the row with the reason. It is not retried automatically.
            with Session() as s, s.begin():
                SilverRepository(s).mark_bronze_failed(doc.id, f"{type(exc).__name__}: {exc}")


def reap() -> None:
    """Run periodically: requeue claims whose worker died. Keep the window well
    above the slowest batch."""
    with Session() as s, s.begin():
        SilverRepository(s).release_stale(timedelta(minutes=30))
```

- **`claim_bronze(limit)`** takes the oldest `UNPROCESSED` rows (by `fetched_at`) with
  `SELECT … FOR UPDATE SKIP LOCKED` and flips them to `PROCESSING`. Any number of
  workers can run it concurrently; each gets disjoint rows, and none blocks on another
  (tested with two live connections, committed and uncommitted).
- **`mark_bronze_processed(ids)`** takes a list, so a batch writer can mark many rows
  in one statement; per-row marking inside the page's transaction, as above, is the
  safer default.
- **`mark_bronze_failed(id, error)`** records the reason in
  `crawled_documents.processing_error` (not `error`, which is the scraper's fetch
  error). FAILED rows stay parked until someone resets them to `UNPROCESSED`; the
  next claim clears the old error.
- **`release_stale(older_than)`** returns `PROCESSING` rows whose claim (`updated_at`)
  is older than the window to `UNPROCESSED`. A too-short window double-processes live
  rows — harmless, since `save_page` is idempotent, but wasted work.

Non-Python writers: the claim is one statement —

```sql
UPDATE crawled_documents SET processing_status = 'PROCESSING',
       processing_error = NULL, updated_at = now()
WHERE id IN (SELECT id FROM crawled_documents
             WHERE processing_status = 'UNPROCESSED'
             ORDER BY fetched_at, id LIMIT $1
             FOR UPDATE SKIP LOCKED)
RETURNING *;
```

---

## 5. Identity, recrawls and reprocessing

| Level | Key | Meaning |
|---|---|---|
| Bronze | `(normalized_url, content_hash)` | one fetched version of a URL |
| Silver | `canonical_url` **UNIQUE** | one page per URL — the upsert key |
| Silver | `crawled_document_id` | the newest Bronze version the page reflects (not unique) |
| Silver | `duplicate_of_id` | mirrored content folded into a canonical page |

- **Recrawl with changed content** → Bronze inserts a new row (new `content_hash`) →
  `save_page` for the same `canonical_url` updates the existing page and repoints
  `crawled_document_id` at the new row.
- **"Newest" is the highest `crawled_documents.id`.** If an older Bronze row is
  processed after a newer one (retry, backfill), `save_page` leaves the page, its tags
  and its contacts untouched and returns `SaveResult(inserted=False)` for the existing
  page. Mark the old Bronze row processed as usual.
- **Running the ETL N times over the same row** yields one page, one set of tags, one
  set of contacts. `SaveResult.inserted` / `.duplicate` says which happened
  (`RETURNING id, (xmax = 0)`).
- **Children are replaced, not merged**: a corrected geo tag replaces the wrong one.
  `replace_children=False` keeps the existing ones.
- **Every save re-queues the page for indexing** (`processing_status = UNPROCESSED`),
  so changed content reaches OpenSearch.
- **Bronze rows behind a page cannot be deleted** (`ON DELETE RESTRICT`). Bronze
  retention must repoint or delete the page first.

Exact (SHA256) and fuzzy (SimHash) dedup across *different* URLs is the ETL's
decision: Spark picks the canonical page and calls
`mark_duplicate_of(page_id, canonical_page_id)`. The database stores `content_hash`
and `sim_hash` so the decision can be made and audited, and rejects a page that
claims to be a duplicate of itself.

## 6. Errors and transactions

| Situation | Behaviour |
|---|---|
| Missing `source_url`, `searchable_text` or `content_hash` | `ValueError` before any SQL |
| Geo tag with a level but no `method` / `confidence` | `ValueError` before any SQL; no page is written |
| Unknown `method`, or `confidence` outside 0–1 | `ValueError` before any SQL (and a CHECK behind it) |
| Unrecognised `language_detected` | stored as `OTHER`, not an error |
| A stored `language` / `method` outside the enum (raw SQL) | CHECK violation (`ck_pages_language`, `ck_page_geo_tags_geo_tag_method`) |
| Unknown `province_code` / `district_code` / `municipality_id` | FK violation, raised — the ETL should `mark_bronze_failed` |
| Geo block with nothing resolved | skipped, not an error |
| Unknown `crawled_document_id` | FK violation, raised |
| Page deleted | tags and contacts cascade |

Nothing in `SilverRepository` commits. The caller owns the transaction, so one page
plus its tags, contacts and Bronze status land as a single unit of work or not at all —
tested, including that a Silver rollback leaves Bronze untouched.

## 7. Enums

Stored as `VARCHAR` + `CHECK`, like every enum in `pgs_db.enums`.

| Enum | Values |
|---|---|
| `Language` | `NE`, `EN`, `MIXED`, `OTHER` |
| `GeoTagMethod` | `GAZETTEER` (name matched in text), `NER`, `DOMAIN` (site belongs to a local body), `GEO_META` (geo meta tags / structured data) |
| `ContactType` | `EMAIL`, `PHONE`, `SOCIAL` |
| `ProcessingStatus` | `UNPROCESSED`, `PROCESSING`, `PROCESSED`, `FAILED` |

---

## 8. Search indexer

Silver is the indexer's source. It polls `pages` for `processing_status = UNPROCESSED`
and reports back with `mark_processed(page_id)` or `mark_processed(page_id, error=...)`.
Key OpenSearch documents on `pages.id` (or `canonical_url`); the old `document_id` no
longer exists.

## 9. Open questions for the ETL/Spark team

1. **No Spark implementation exists to verify against.** Confirm this contract when the
   real transform lands.
2. **§5.2 has no `method` / `confidence` / `mention_text` on `geo_location`.** They are
   required here for any resolved tag. §5.2 needs updating, or every tagged page fails.
3. **§5.2 has no `word_count`.** Optional here: computed by whitespace split if absent.
   Send it if Spark tokenizes Nepali differently.
4. **`content_hash` is not in the §5.2 payload.** Pass it explicitly from the Bronze row
   (as the loop above does), or add it to the payload.
5. **`published_at` and `content_type` are in `SearchDocument` but not §5.2.** Both are
   optional here.
6. **`D38` vs `D39` for Kaski** — §5.2's example disagrees with the seeded gazetteer. The
   seeded values are authoritative.
7. **The Kafka consumer writes SQLite** (`ETL/kafka/consumer.py`), not PostgreSQL, and its
   `documents` table duplicates Bronze. Nothing currently bridges it to this layer.
