# ER diagram

This file is the source of truth for the schema diagram; GitHub renders the blocks below.
`pgs_search_engine_full_erd.png` is generated from it — after editing, run
`python scripts/render_erd.py` (needs Node) and commit both.

Status per table: **built** = in a migration today · **planned** = agreed, not built yet.
Every table also has `created_at` and `updated_at` (timestamptz, UTC). Enum columns are
`VARCHAR` + `CHECK`, with the values in `src/pgs_db/enums.py`.

## Changes from the original PNG (agreed with the ETL group, 2026-09-26)

| Change | Why |
|---|---|
| `page_links` dropped | Links already live on Bronze (`links`, `internal_links`, `external_links`, `anchor_texts`). PageRank and `domain_stats.inbound_link_count` are computed from those arrays in Spark. |
| `pages.host` dropped | Duplicates `pages.domain_id → domains.domain`; the raw host stays in Bronze. |
| `pages.canonical_url` **kept** | It is the page's identity: the upsert key that makes a recrawl update one page instead of duplicating it, and the URL search results show. The ETL no longer has to send it — `save_page` falls back to the Bronze row's `normalized_url`. |
| `document_embeddings` (Gold) → `page_embeddings` (Silver) | `search_documents` is 1:1 with `pages`, so keying embeddings on the page removes a hop and lets ETL write them before Gold exists. Stored in Postgres with pgvector, 384 dimensions: the search team's query model (`all-MiniLM-L6-v2`) and their `pgvector_search.py` set both. |
| Geo links use **codes**, not ids | `page_geo_tags` references `provinces.code` / `districts.code` / `local_bodies.code`, the codes ETL and search already exchange (`P4`, `D38`, `MUN414`). Gold follows the same rule. |
| A page's source is a crawled page **or** a stored file | `pages.stored_file_id` (CHECK: exactly one of it and `crawled_document_id`) so PDFs and images in MinIO become searchable pages. |
| `entities.type` has no LOCATION | Places are `page_geo_tags` against the gazetteer; a second place list would drift from it. |
| `page_geo_mentions` → `page_geo_tags`, plus `page_contacts` | As built. `page_geo_tags` adds `ward_number`, drops `char_start`/`char_end`. `page_contacts` holds per-page emails, phones and social links. |

## Reference — built

```mermaid
erDiagram
    provinces ||--o{ districts : contains
    districts ||--o{ local_bodies : contains
    local_bodies |o--o{ domains : "official site of"

    provinces {
        bigint id PK
        varchar code UK "P1..P7"
        varchar name_en
        varchar name_ne
    }
    districts {
        bigint id PK
        varchar code UK "D01..D77"
        varchar province_code FK
        varchar name_en
        varchar name_ne
    }
    local_bodies {
        bigint id PK
        varchar code UK "MUN001..MUN753"
        varchar district_code FK
        varchar type "LocalBodyType"
        varchar name_en
        varchar name_ne
        varchar website
        varchar phone "empty in seed data"
        varchar email "empty in seed data"
        varchar address "empty in seed data"
    }
    domains {
        bigint id PK
        varchar domain UK
        varchar website_name
        varchar category "DomainCategory"
        varchar status "DomainStatus"
        varchar priority "DomainPriority"
        int rate_limit_per_sec
        bigint local_body_id FK "nullable"
        timestamptz last_crawled_at
    }
```

## Bronze — built

```mermaid
erDiagram
    crawl_runs |o--o{ crawled_documents : produced
    domains |o--o{ crawled_documents : hosts
    crawled_documents |o--o{ stored_files : links_to

    crawl_runs {
        bigint id PK
        varchar category
        varchar status "CrawlRunStatus"
        varchar temporal_workflow_id
        timestamptz started_at
        timestamptz finished_at
        int fetched_count
        int succeeded_count
        int failed_count
        int skipped_count
        int unique_url_count
    }
    crawled_documents {
        bigint id PK
        bigint crawl_run_id FK "nullable"
        bigint domain_id FK "nullable"
        text url
        text normalized_url UK "UQ with content_hash; the page identity"
        text final_url
        text canonical_url
        varchar host
        varchar category
        text_and_arrays content "title, meta_*, open_graph, text, headings, json_ld"
        arrays contacts "emails, phones, address, social_links"
        arrays links "links, anchor_texts, internal/external/image/video_links"
        float geo_lat
        float geo_lng
        varchar country
        bigint sim_hash
        int depth
        int status_code
        varchar content_type
        varchar content_hash UK "UQ with normalized_url"
        timestamptz fetched_at
        bigint fetch_duration_ms
        text error
        text minio_path
        varchar processing_status "ETL work queue"
        text processing_error
    }
    stored_files {
        bigint id PK
        bigint crawled_document_id FK "nullable"
        text source_page_url
        text document_url UK "UQ with sha256"
        text storage_path
        varchar content_type
        varchar sha256 UK "UQ with document_url"
        bigint size_bytes
        timestamptz stored_at
        varchar processing_status "ETL work queue for files"
        text processing_error
    }
```

## Silver — built

```mermaid
erDiagram
    crawled_documents |o--o{ pages : "newest version of"
    stored_files |o--o{ pages : "file page of"
    domains |o--o{ pages : hosts
    pages |o--o{ pages : duplicate_of
    pages ||--o{ page_geo_tags : tagged
    pages ||--o{ page_contacts : lists
    pages ||--o{ page_embeddings : embedded
    pages ||--o{ page_sources : "fetch history"
    crawled_documents |o--o{ page_sources : "source of"
    stored_files |o--o{ page_sources : "source of"
    pages ||--o{ page_media : contains
    stored_files |o--o{ page_media : "file for"
    pages ||--o{ page_entities : mentions
    entities ||--o{ page_entities : "mentioned in"

    pages {
        bigint id PK
        bigint crawled_document_id FK "exactly one of this or stored_file_id"
        bigint stored_file_id FK "a PDF or image page"
        bigint domain_id FK
        text canonical_url UK "falls back to the source URL"
        text title
        text description
        text body_text
        int word_count
        text_array keywords
        varchar language
        float language_confidence "0..1"
        varchar content_type
        varchar category
        varchar author
        timestamptz published_at
        text_array quality_flags
        varchar content_hash
        bigint sim_hash
        bigint duplicate_of_id FK
        timestamptz first_seen_at
        timestamptz last_seen_at
        int version "+1 per content change"
        varchar processing_status "indexer queue"
        text processing_error
    }
    page_geo_tags {
        bigint id PK
        bigint page_id FK
        varchar province_code FK "nullable"
        varchar district_code FK "nullable"
        varchar local_body_code FK "nullable"
        int ward_number
        varchar method "GeoTagMethod"
        float confidence "0..1"
        text mention_text
    }
    page_contacts {
        bigint id PK
        bigint page_id FK
        varchar type "EMAIL, PHONE, SOCIAL"
        text value "UQ with page_id, type"
    }
    page_embeddings {
        bigint id PK
        bigint page_id FK
        varchar model_name "UQ with page_id, chunk_index"
        varchar model_version
        int chunk_index
        text chunk_text
        vector embedding "vector 384, HNSW cosine index"
        varchar content_hash "page text it was made from"
        timestamptz embedded_at
    }
    page_sources {
        bigint id PK
        bigint page_id FK
        bigint crawled_document_id FK "exactly one of the two"
        bigint stored_file_id FK
        timestamptz fetched_at
        boolean content_changed
    }
    page_media {
        bigint id PK
        bigint page_id FK
        bigint stored_file_id FK "nullable"
        text url "UQ with page_id"
        varchar media_type "IMAGE, VIDEO, DOCUMENT"
        text alt_text
        text extracted_text "OCR or parsed text"
    }
    entities {
        bigint id PK
        varchar normalized_key UK "TYPE:casefolded name"
        varchar type "PERSON, ORGANIZATION, EVENT, OTHER"
        varchar name_en
        varchar name_ne
    }
    page_entities {
        bigint id PK
        bigint page_id FK "UQ with entity_id"
        bigint entity_id FK
        int mention_count
        float salience "0..1"
    }
```

## Gold — planned

Blocked on PostGIS: `search_documents.geom` is `geometry(Point, 4326)`.

```mermaid
erDiagram
    pages ||--o| search_documents : "served as"
    domains ||--o| domain_stats : summarised
    search_documents ||--o{ document_geo : placed
    search_queries ||--o{ search_clicks : led_to
    search_documents ||--o{ search_clicks : clicked

    search_documents {
        bigint id PK
        bigint page_id FK "UQ"
        bigint domain_id FK
        text url
        text title
        text snippet
        text body_text
        varchar language
        varchar category
        timestamptz published_at
        varchar primary_province_code FK
        varchar primary_district_code FK
        varchar primary_local_body_code FK
        geometry geom "Point 4326, needs PostGIS"
        tsvector search_vector
        float pagerank "from Bronze link arrays"
        float quality_score
        float freshness_score
        float static_rank
        varchar es_doc_id UK
        timestamptz indexed_at
        varchar index_status
    }
    document_geo {
        bigint id PK
        bigint search_document_id FK
        varchar province_code FK
        varchar district_code FK "nullable"
        varchar local_body_code FK "nullable"
        float weight
        boolean is_primary
    }
    geo_content_stats {
        bigint id PK
        varchar admin_level
        varchar province_code FK "nullable"
        varchar district_code FK "nullable"
        varchar local_body_code FK "nullable"
        varchar category
        varchar language
        date period_date
        int doc_count
        int domain_count
        timestamptz latest_published_at
    }
    domain_stats {
        bigint id PK
        bigint domain_id FK "UQ"
        int page_count
        int indexed_count
        int inbound_link_count "from Bronze link arrays"
        float authority_score
        float avg_quality_score
        timestamptz last_indexed_at
    }
    search_queries {
        bigint id PK
        varchar session_id
        text query_text
        varchar query_language
        text translated_text
        jsonb filters
        int result_count
        int latency_ms
        timestamptz searched_at
    }
    search_clicks {
        bigint id PK
        bigint search_query_id FK
        bigint search_document_id FK
        int rank_position
        timestamptz clicked_at
    }
```
