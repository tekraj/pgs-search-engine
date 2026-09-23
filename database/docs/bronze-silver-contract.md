# Bronze → Silver contract (for the Spark ETL)

How the Spark ETL writes the Silver layer. The Python reference implementation is
`pgs_db.repositories.SilverRepository`; `tests/test_silver.py` proves every rule below
against a real PostgreSQL using payloads copied verbatim from `ETL/spark/README.md` §5.2.

Schema version: Alembic revision `e529ca38e6ae`.

```text
crawled_documents  (Bronze)
        │  1:1 on crawled_document_id
        ▼
      pages        (Silver)
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

Nothing here was invented. **However, no Spark transform exists yet**:
`ETL/spark/test_spark.py` is a PySpark hello-world, and the Airflow DAG is labelled
"dummy ... Spark will do this for real later". This contract therefore encodes the
*documented* output, not observed output. When the real transform lands, the first
thing to check is §6.

## 2. Two §5.2 fields are deliberately not stored

| §5.2 field | Where it goes instead | Why |
|---|---|---|
| `searchable_text` | OpenSearch | Full page text is not PostgreSQL's job. Bronze already keeps the extracted text as provenance (`crawled_documents.text`), so re-indexing never needs a re-fetch. |
| `geo_location.*_name_en` / `*_name_ne` / `municipality_type` | joined from the gazetteer | 837 reference rows duplicated onto every page would drift. `GeoLocationOut.from_tag()` rebuilds the block exactly as §5.2 shows it. |

Everything else in §5.2 has a column.

---

## 3. `pages`

One clean record per Bronze document.

| Column | Type | Req. | Source |
|---|---|---|---|
| `id` | `BIGINT` | auto | — |
| `crawled_document_id` | `BIGINT` **UNIQUE** | yes | FK → `crawled_documents.id`, `ON DELETE CASCADE` |
| `domain_id` | `BIGINT` | no | FK → `domains.id` |
| `document_id` | `VARCHAR(64)` **UNIQUE** | yes | §5.2 `document_id` |
| `source_url` | `TEXT` | yes | §5.2 `source_url` |
| `title` | `TEXT` | no | §5.2 `extracted_metadata.title` |
| `description` | `TEXT` | no | §5.2 `extracted_metadata.description` |
| `keywords` | `TEXT[]` | no | §5.2 `extracted_metadata.keywords` |
| `language` | `VARCHAR(16)` | yes (`"unknown"`) | §5.2 `language_detected`, or `SearchDocument.language` |
| `content_type` | `VARCHAR(32)` | yes (`"web_page"`) | `SearchDocument.content_type` |
| `published_at` | `TIMESTAMPTZ` | no | `SearchDocument.published_at` |
| `content_hash` | `VARCHAR(64)` | yes | Bronze `content_hash` (ETL §3 exact dedup) |
| `sim_hash` | `BIGINT` | no | Bronze `sim_hash` (ETL §3 fuzzy dedup) |
| `duplicate_of_id` | `BIGINT` | no | self-FK, `ON DELETE SET NULL`. NULL = canonical |
| `processing_status` | `VARCHAR(32)` | yes (`UNPROCESSED`) | downstream indexing state |
| `processing_error` | `TEXT` | no | why indexing failed |
| `created_at` / `updated_at` | `TIMESTAMPTZ` | auto | UTC |

Indexes: `processing_status`, `content_hash`, `published_at`, `domain_id`, `duplicate_of_id`.

## 4. `page_geo_tags`

| Column | Type | Req. | Source |
|---|---|---|---|
| `page_id` | `BIGINT` | yes | FK → `pages.id`, `ON DELETE CASCADE` |
| `province_code` | `VARCHAR(4)` | no | §5.2 `geo_location.province_code`, FK → `provinces.code` |
| `district_code` | `VARCHAR(4)` | no | §5.2 `geo_location.district_code`, FK → `districts.code` |
| `local_body_id` | `BIGINT` | no | resolved from §5.2 `geo_location.municipality_id` via `local_bodies.code` |
| `ward_number` | `INTEGER` | no | §5.2 `geo_location.ward_number` |

**All three levels are nullable, but at least one must be present** —
`CHECK ck_page_geo_tags_at_least_one_level`. Resolution is partial in practice: a
municipality site resolves to a local body, a national news article may only reach a
district. `ward_number`, when given, must be positive.

A page may have **several** tags: `save_page` accepts `geo_location` as one object
(§5.2) or a list.

Send codes, not names. `municipality_id` is the gazetteer code (`MUN414`), which this
layer resolves to `local_bodies.id`. An unrecognised code resolves to `NULL` rather
than failing — the other levels still store. Codes are documented in the database
README; note that §5.2's example uses `D39` for Kaski, but the seeded gazetteer has
Kaski at **`D38`** (`D39` is Lamjung).

## 5. `page_contacts`

| Column | Type | Req. | Source |
|---|---|---|---|
| `page_id` | `BIGINT` | yes | FK → `pages.id`, `ON DELETE CASCADE` |
| `type` | `VARCHAR(32)` | yes | `EMAIL` / `PHONE` / `SOCIAL` |
| `value` | `TEXT` | yes | the address, number or URL |

Bronze keeps three parallel arrays (`emails`, `phones`, `social_links`); Silver
normalizes them into rows so the API can ask "every phone number for pages in Kaski"
without unnesting arrays. `UNIQUE (page_id, type, value)`.

Read from `extracted_metadata.contact_info.emails` / `.phones`, and `social_links`
from either `contact_info` or `extracted_metadata`.

---

## 6. Deduplication rules

Three different identities, easily confused:

| Level | Key | Meaning |
|---|---|---|
| Bronze | `(normalized_url, content_hash)` | one fetched version of a URL |
| Silver | `crawled_document_id` **UNIQUE** | one page per Bronze row — the reprocessing key |
| Silver | `document_id` **UNIQUE** | the ETL's stable public id |
| Silver | `duplicate_of_id` | mirrored content folded into a canonical page |

ETL §3 describes exact (SHA256) and fuzzy (SimHash) dedup. Both are **the ETL's
decision, not the database's**: Spark decides which page is canonical and calls
`mark_duplicate_of(page_id, canonical_page_id)`. The database stores `content_hash`
and `sim_hash` so that decision can be made and audited, and rejects a page that
claims to be a duplicate of itself.

## 7. Retry and reprocessing behaviour

Reprocessing is the normal case — Spark re-runs, Airflow backfills, nightly deep-dedup
re-emits. Every write is keyed so re-running converges:

- **`save_page` upserts on `crawled_document_id`.** Running the ETL five times over the
  same Bronze row yields one page, one set of tags, one set of contacts (tested).
- **`SaveResult.inserted` / `.duplicate`** tells you which happened, in the same round
  trip (`RETURNING id, (xmax = 0)`).
- **Children are replaced, not merged.** Reprocessing re-derives geo tags and contacts
  from the new payload, so a corrected geo tag *replaces* the wrong one instead of
  sitting beside it. Pass `replace_children=False` to keep the existing ones.
- **`document_id` and `crawled_document_id` are never overwritten** by an upsert; they
  are the identity.
- `page_geo_tags`'s unique constraint uses `NULLS NOT DISTINCT` (PostgreSQL 15+), so a
  partially-NULL location does not slip past it and duplicate.

## 8. Stable IDs

`document_id` must be stable across reprocessing — the search index keys on it.

If Spark sends `document_id`, it wins. If it is omitted, this layer derives
`doc_<first 12 hex of content_hash>`, which is stable by construction: same content,
same id. Once Spark emits its own, that value is used instead.

`crawled_document_id` is the *internal* stable key. `document_id` is the public one.

## 9. Errors and transactions

| Situation | Behaviour |
|---|---|
| Missing `source_url` or `content_hash` | `ValueError` before any SQL — the row cannot half-write |
| Unknown `municipality_id` | resolves to `NULL`; other levels still store |
| Geo block with nothing resolved | skipped, not an error — most pages are not about a place |
| Unknown `crawled_document_id` | FK violation, raised |
| Duplicate `document_id` | unique violation, raised |
| Page deleted | tags and contacts cascade |

Nothing in this layer commits. The caller owns the transaction, so one page plus its
tags and contacts land as a single unit of work or not at all — tested, including that
a Silver rollback leaves Bronze untouched.

## 10. Open questions for the ETL/Spark team

1. **No Spark implementation exists to verify against.** This contract encodes §5.2 as
   written. Confirm it when the real transform lands.
2. **`content_hash` is not in the §5.2 payload** but Silver needs it for dedup. Today it
   is passed alongside the payload (from the Bronze row). Either add it to the payload
   or keep passing it explicitly.
3. **`published_at` and `content_type` are in `SearchDocument` but not §5.2.** Both are
   optional here. Spark should emit them if the search team needs them populated.
4. **`municipality_type` in §5.2 is redundant** — it is `local_bodies.type` and comes
   back from the join. Nothing is lost; flagging so nobody expects a column.
5. **`D38` vs `D39` for Kaski** — §5.2's example disagrees with the seeded gazetteer.
   The seeded values are authoritative.
6. **The Kafka consumer writes SQLite** (`ETL/kafka/consumer.py`), not PostgreSQL, and
   its `documents` table duplicates Bronze. Nothing currently bridges it to this layer.
