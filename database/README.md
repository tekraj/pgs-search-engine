# Database (`pgs-db`)

We design and manage the PostgreSQL database that the scraper, ETL, search engine and API all share.

**Status:** Bronze, Silver and the reference tables are built and migrated. Gold and the
operational tables are still to come — see [§5](#5-table-status).

---

## 1. What the database is for

The database is the project's **record book**. It does not hold the actual web pages. It holds **information about them**:

- which websites we crawl and their status
- which files were downloaded and where they are stored
- clean page details (title, language, date)
- which province, district and municipality each page belongs to
- admin users, blocked files and error logs

## 2. What goes where

| Data | Stored in |
|---|---|
| Raw HTML, PDFs, documents | **MinIO** (not the database) |
| Full page text for searching | **OpenSearch** |
| "Already visited" URL list | **Redis** |
| Records, status, relationships, locations | **PostgreSQL (this group)** |

If you are unsure where your data should go, ask us.

`crawled_documents.text` is the one deliberate exception: Bronze keeps the scraper's extracted
text as provenance, so a page can be re-processed without re-fetching it. Search still reads
from OpenSearch, never from this column.

## 3. How data is organised

The full ER diagram, with what is built and what is planned, is in
[`docs/erd.md`](docs/erd.md); `pgs_search_engine_full_erd.png` is rendered from it by
`python scripts/render_erd.py`.

We use three layers:

| Layer | Meaning | Tables | Status |
|---|---|---|---|
| **Bronze** | Raw: a record of every crawl and every downloaded file, unchanged | `crawl_runs`, `crawled_documents`, `stored_files` | **Built** |
| **Silver** | Clean: one record per page, duplicates removed, location tagged | `pages`, `page_geo_tags`, `page_contacts`, `page_sources`, `page_media`, `entities`, `page_entities`, `page_embeddings`, `quarantined_files` | **Built** |
| **Gold** | Ready to use: summaries for the map and dashboard | `district_stats`, `domain_stats` | Planned |

Plus **reference tables** that everything links to:

- `provinces` (7), `districts` (77), `local_bodies` (753) — built and fully seeded
- `domains`: the list of websites to crawl — built
- `admin_users` — planned

## 4. What is built

Five migrations are in place: `95e7b8aa6ec5` (Bronze + reference), `e529ca38e6ae` (Silver),
`e6aa9e30d49a` (pages built from stored files, `stored_files.processing_error`) and
`ac08008a1fbf` (the rest of Silver; enables pgvector) and `8aa170eaaf03`
(`quarantined_files`, and `QUARANTINED` as a processing status).

| Table | Layer | Written by | Read by | Mirrors |
|---|---|---|---|---|
| `crawl_runs` | Bronze | Scraper | API | scraper `CrawlStats` / `Document.crawl_run_id` |
| `crawled_documents` | Bronze | Scraper | ETL, API | scraper `model.Document` |
| `stored_files` | Bronze | Scraper | ETL, API | scraper `model.StoredDocument` |
| `domains` | Reference | API (admin) | Scraper, ETL | the seed registry / domain→municipality map |
| `provinces` | Reference | Database group | ETL, API, UI | search `GeoLocation.province_code` |
| `districts` | Reference | Database group | ETL, API, UI | search `GeoLocation.district_code` |
| `local_bodies` | Reference | Database group | ETL, API, UI | search `GeoLocation.municipality_id` |

Design decisions worth knowing:

- **Dedupe identity** is `UNIQUE (normalized_url, content_hash)` on `crawled_documents`. Two URLs
  that declare the same canonical collapse to one row; the same URL with changed content becomes
  a new row.
- **Statuses are `VARCHAR` + `CHECK`**, not native Postgres enums, so the Go scraper and Spark can
  insert plain strings with no casts. Values live in `src/pgs_db/enums.py`.
- **All primary keys are `BIGINT`**, matching the scraper's `int64` ids.
- **All timestamps are `timestamptz`**, stored in UTC.

**Note for the Go scraper:** `sim_hash` is `uint64` in Go but Postgres has no unsigned type. Write
`int64(simHash)` and read back with `uint64(v)`; the bits are unchanged, so Hamming distance still
works.

## 5. Table status

| Table | Layer | Status |
|---|---|---|
| `crawl_runs` | Bronze | Built |
| `crawled_documents` | Bronze | Built |
| `stored_files` | Bronze | Built |
| `domains` | Reference | Built |
| `provinces` | Reference | Built, seeded (7) |
| `districts` | Reference | Built, seeded (77) |
| `local_bodies` | Reference | Built, seeded (753) |
| `pages` | Silver | Built — ETL output, from a crawled page or a stored file (PDF, image) |
| `page_geo_tags` | Silver | Built — province/district/municipality/ward per page |
| `page_contacts` | Silver | Built — emails, phones, socials per page |
| `page_sources` | Silver | Built — every Bronze row that fed a page (history) |
| `page_media` | Silver | Built — images, videos, linked documents, with OCR/parsed text |
| `entities` / `page_entities` | Silver | Built — people, organizations, events per page |
| `page_embeddings` | Silver | Built — pgvector, 384 dimensions, HNSW cosine index |
| `quarantined_files` | Silver | Built — files ClamAV flagged during ETL; the API's quarantine audit |
| `district_stats` | Gold | Not built — page counts for the UI map |
| `domain_stats` | Gold | Not built — pages scraped/failed per domain |
| `error_logs` | Ops | Not built — all services write here |
| `admin_users` | Ops | Not built — API auth |

### Reference data (the gazetteer)

`data/nepal_geography.json` holds all 837 rows and is committed, so seeding needs no network.
`scripts/seed_geography.py` upserts it on `code`, so it is safe to re-run.

Source: [sagautam5/local-states-nepal](https://github.com/sagautam5/local-states-nepal). Counts
match the official split exactly — 6 metropolitan, 11 sub-metropolitan, 276 municipalities,
460 rural municipalities = 753.

**Codes are assigned by this project**, not taken from an official registry:

| Level | Format | Example |
|---|---|---|
| Province | `P1`–`P7` | `P4` = Gandaki |
| District | `D01`–`D77` | `D38` = Kaski |
| Local body | `MUN001`–`MUN753` | `MUN414` = Pokhara Metropolitan City |

Districts and local bodies are numbered by the source dataset's own ordering (grouped by province,
then alphabetically). **This is the contract for `GeoLocation.district_code` and
`municipality_id`** — if the search or ETL team needs a different scheme, raise it before the
gazetteer is used in anger, because changing it later means re-tagging every page.

> Note: `ETL/README.md` §5.2 uses `D39` for Kaski in its worked example. In the seeded data Kaski
> is `D38` and `D39` is Lamjung. The ETL example was illustrative; the seeded values are the ones
> to code against.

Two known gaps in the reference data: `local_bodies.phone`, `.email` and `.address` are empty
(only `website` is populated, for all 753), and the source's ward counts are carried in the JSON
but not loaded, since the table has no ward-count column.

### What's next (from a review of every branch, refreshed 2026-09-26)

**This branch (`db`)**

- **Merge `master` in, then open the PR.** Nothing here is usable by other groups until it is
  on `master`. `db` is one commit behind (`94736bf`, a scraper doc; no conflict expected).
- **Silver is complete** (migration `ac08008a1fbf`): `page_sources` (fetch history),
  `page_media` (images/PDFs with OCR text), `entities` + `page_entities` (NER),
  `page_embeddings` (pgvector, 384 dimensions) and the remaining `pages` columns. The ETL
  loop is ready-made in `pgs_db.etl`. See
  [`docs/bronze-silver-contract.md`](docs/bronze-silver-contract.md).
- **Everyone must rebuild the database image**: `docker compose up -d --build`. The new
  `Dockerfile` adds pgvector to PostGIS; `alembic upgrade head` fails on the old image
  (`extension "vector" is not available`). Data volumes are kept.
- **`biyush/database-schemas` is superseded, and its import is broken.** Its District,
  LocalBody and domain-hostname validation are now on `db` (`schemas/geography.py`,
  `schemas/bronze.py`). On his branch, `class LocalBodyBase` is indented inside
  `DistrictRead`, so `LocalBodyCreate` raises `NameError` on import. Its `crawl.py`
  duplicates `schemas/bronze.py`. Tell Biyush, and close the branch.
- **`quarantined_files` (Silver) is built** for the ETL to record ClamAV hits
  (`SilverRepository.quarantine`, or raise `pgs_db.etl.Infected` from a transform), and
  for the API's security endpoints (`QuarantineRepository`). Nobody runs ClamAV yet, and
  the ETL README's Stage 2 still places the scan on the scraper side: settle that with
  both teams (contract §10 q9).
- **Next to build: Gold.** `geo_content_stats` and `domain_stats` first (the API's map and
  admin endpoints need them; no PostGIS needed), then enable PostGIS for
  `search_documents` / `document_geo`.

**Other teams (each one writes to or reads from our tables)**

- **Scraper: two Bronze schemas.** `person1/search-engine-scaffold` now has a working
  Postgres writer (`scraper/internal/storage/postgres.go`), but against **its own**
  migrations (`scraper/migrations/0001`–`0010`): a `documents` table instead of
  `crawled_documents`, a different `crawl_runs` (`fetched`, `seed_count`, ...), no
  `stored_files`, no `domains`. Its migration 0009 also changed the key to one row per
  `normalized_url`, updated in place, where ours keeps one row per content version,
  which `page_sources` and Silver's recrawl logic rely on. The two can't both be Bronze.
  Proposal: the scraper drops its migrations and writes our tables per
  [`docs/scraper-db-contract.md`](docs/scraper-db-contract.md), rewriting its `sqlc`
  queries (`scraper/internal/db/queries.sql`) against them. Its freshness check has an
  equivalent in `BronzeRepository.last_fetched_at`. This needs a meeting with the scraper
  team, not a unilateral change.
- **ETL is waiting on us** (`ETL/kafka/phase1_testing/README.md`: "ETL -> Postgres write
  path not built yet, pending schema sync with the database team"). Point them at
  `pgs_db.etl.process_bronze_batch`: they write only the transform (`ETL/spark/transform.py`
  is still a placeholder). Two things to raise: geo tags need `method` + `confidence`
  (contract §10 q2); the Kafka consumer still saves to SQLite.
- **Search: embeddings model.** `pgs_search/query/embeddings.py` (`rabin/grpc-search-service`,
  `search-engine`) uses `all-MiniLM-L6-v2`, which is English-only, so Nepali pages will embed
  poorly. `paraphrase-multilingual-MiniLM-L12-v2` is also 384-dimension, so switching needs
  no migration. Their `pgvector_search.py` queries a `documents` table: point it at
  `page_embeddings` (`SilverRepository.nearest_chunks` does the query) with geo filters
  joined through `page_geo_tags`.
- **Search: `SearchDocument.document_id`** (`feat/image-ingestion`,
  `shreya/bilingual-query-normalization`) no longer exists; use `pages.id` /
  `canonical_url`. Image OCR (`feat/image-ingestion`) now has a home: `page_media.extracted_text`.
- **Seed categories (`omprakash/search-engine-scrapper`) are free text** (`[news]`,
  `[tech 10]`), but `domains.category` only accepts `DomainCategory` values. Agree on a
  mapping, and have seeding upsert `domains`.
- **API geo and crawl-stats endpoints** (`api/README.md` §3.2, admin stats) can be served from
  `provinces` / `districts` / `local_bodies` and `crawl_runs` today.

### Writing the Bronze tables

`pgs_db.BronzeRepository` is the only code that writes `crawl_runs`, `crawled_documents`,
`stored_files` and `domains`. Python services use it directly:

```python
from pgs_db import BronzeRepository, make_session_factory

with make_session_factory().begin() as session:
    repo = BronzeRepository(session)
    run_id = repo.start_crawl_run(category="government")
    result = repo.save_document(document_json, crawl_run_id=run_id)
    if result.duplicate:
        ...  # same URL and content already stored
    repo.finish_crawl_run(run_id, stats=crawl_stats)
```

It takes the scraper's JSON as-is and handles the conversions that JSON needs (`crawl_run_id: 0`
→ NULL, `omitempty` blanks → NULL, `uint64` simhash → `int64`, nested `geo`/`contact_info`
flattened). Non-Python services issue the same statements by hand —
[`docs/scraper-db-contract.md`](docs/scraper-db-contract.md) lists them, along with the columns that must
always be sent and the duplicate/failure rules.

`pgs_db.SilverRepository` does the same job for the Silver tables, taking the Spark ETL's
output payload and landing it in `pages`, `page_geo_tags` and `page_contacts` —
see [`docs/bronze-silver-contract.md`](docs/bronze-silver-contract.md).

## 6. Rules everyone should follow

1. **Don't create or change tables yourself.** Ask the Database group. All changes go through migrations (Alembic) so everyone stays in sync.
2. **Never store file contents in PostgreSQL.** Store the MinIO path instead.
3. **All times in UTC.**
4. **Use the fixed status values** we publish in `src/pgs_db/enums.py`, e.g. `PENDING`, `CRAWLING`, `COMPLETED`, `FAILED`.
5. **Python services** can use our package: `pip install -e ./database`, then `import pgs_db`.
6. **Non-Python services** (Go scraper, Spark) write to the same tables using the column list we publish.

## 7. Quick start 

Needs **Docker Desktop** (running) and **Python 3.11+**.

```bash
cd database
cp .env.example .env                  # Windows: copy .env.example .env
docker compose up -d --build          # PostgreSQL 16 + PostGIS + pgvector (./Dockerfile)
pip install -e ".[postgres,dev]"

export DATABASE_URL=postgresql+psycopg://pgs:pgs@localhost:5432/pgs
# Windows PowerShell:
# $env:DATABASE_URL="postgresql+psycopg://pgs:pgs@localhost:5432/pgs"

python -m alembic upgrade head        # create all tables
python scripts/seed_geography.py      # 7 provinces, 77 districts, 753 local bodies
python -m pytest                      # 199 tests should pass
```

The tests need a live database: they read `DATABASE_URL` and each test runs in a transaction that
is rolled back. Without `DATABASE_URL` set, the suite skips rather than fails, so check that
tests actually ran (`199 passed`), not just that the command exited green.

Look inside the database:

```bash
docker exec -it pgs-postgres psql -U pgs -d pgs -c "\dt"
docker exec -it pgs-postgres psql -U pgs -d pgs -c "SELECT * FROM provinces;"
```

**Common problems**

- **`alembic` / `pytest` not recognized:** use `python -m alembic` and `python -m pytest`.
- **`password authentication failed for user "pgs"`:** another PostgreSQL on your PC is using
  port 5432. Add `POSTGRES_PORT=5433` to `.env`, run `docker compose down` then
  `docker compose up -d`, and use port `5433` in `DATABASE_URL`.
- **`column ... does not exist` (e.g. `pages.canonical_url`) although `alembic current` says
  head:** your database was created from an earlier draft of a migration that was later edited
  in place, so Alembic sees nothing to apply. Recreate it (this deletes its data):
  `docker exec pgs-postgres psql -U pgs -d postgres -c "DROP DATABASE pgs WITH (FORCE)" -c "CREATE DATABASE pgs"`,
  then `python -m alembic upgrade head` and `python scripts/seed_geography.py`.
- **`extension "vector" is not available`** during `alembic upgrade head`: the container
  is still on the old PostGIS-only image. Run `docker compose up -d --build`.
- **`connection refused`:** the container is still starting or stopped. Run `docker compose up -d`
  and wait a few seconds.

**Connection URLs**

| Used by | URL |
|---|---|
| Python (SQLAlchemy, Alembic) | `postgresql+psycopg://pgs:pgs@localhost:5432/pgs` |
| Go scraper (`--storage=postgres`) | `postgres://pgs:pgs@localhost:5432/pgs` |
| Other containers in the same compose | host `postgres` instead of `localhost` |

