# System Architecture & Technical Design Specification

## Bilingual Search Engine Core with Spatial Intelligence (Internal Service)

---

## 1. Executive Summary

This document details the architecture for the **Search Engine Core**, a highly scalable, bilingual search engine covering the Nepalese web ecosystem.

**Crucially, this Search Engine exposes no public APIs.** It operates entirely as an internal, backend microservice within a private virtual network. It receives queries and streams results exclusively via high-performance **gRPC** protocols to a dedicated API Gateway layer.

The core pipeline features **Geo-Spatial & Administrative Entity Intelligence**, enabling it to process both standard lexical queries and strict region-bounded administrative searches over its OpenSearch indices.

---

## 2. Core Search Engine Architecture (Internal Network)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SEARCH ENGINE INFRASTRUCTURE (Internal)         │
└────────────────────────────────────────────────────────────────────────┘

 [ Spark ETL: LangID + Geo-Tagging ] ──► [ OpenSearch Bulk Ingestion ]
                                                │
                                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. MULTI-LINGUAL & GEO-INDEXED DOCUMENT STORE (OpenSearch)             │
│    - Indices: `np_web_pages`, `np_documents`, `np_entities`            │
│    - Dual-Analyzers for English/Nepali & nested geo-hierarchy filters  │
└────────────────────────────────────────────────────────────────────────┘
                                                ▲
                                                │
┌───────────────────────────────────────────────┴────────────────────────┐
│ 2. SEARCH ENGINE CORE SERVICE (Go / Python)                            │
│    - Query LangID & Devanagari Normalizer                              │
│    - Admin Code Filter Engine (`province`, `district`, `local_body`)   │
│    - Stage 1: BM25 candidate fetch (with optional hard Geo-Filtering)  │
│    - Stage 2: LightGBM Re-Ranker                                       │
│    - Exposes internal gRPC server (e.g., `SearchService`)              │
└───────────────────────────────────────────────┬────────────────────────┘
                                                │ 
                                                ▼ 
                                   [ Protobuf / gRPC Stream ] 
                                   (To External API Gateway)

```

---

## 3. Query Processing Subsystems

The Search Engine Core listens for incoming gRPC messages containing user intent, location filters, and pagination data. It processes two primary types of searches:

### 3.1 Flow A: Standard Free-Text Search

When a standard query is received via gRPC:

1. **Language Processing:** The core detects the language, applies stemming, and expands Devanagari/Romanized variants.
2. **BM25 Retrieval & LTR Ranking:** OpenSearch retrieves the top 500 matches across ALL regions. The LightGBM model ranks them by relevance, domain authority, and freshness.
3. **Serialization:** The results are packed into a Protobuf message and sent back to the API Gateway.

### 3.2 Flow B: Interactive Map & Region-Based Filtering

When a geo-filtered query is received via gRPC (e.g., bounded to `district_code=D39`):

1. **Filter Application:** The core constructs a strict Boolean OpenSearch query locking the search space to the specified administrative boundaries.
2. **Regional Ranking:** Candidates are fetched and ranked.
3. **Knowledge Assembly:** The core retrieves the specific administrative Knowledge Card (e.g., Official Portal links for Pokhara Municipality) and embeds it in the gRPC response payload.

---

---
## 4. Image Ingestion

Images are made searchable by turning each one into a `SearchDocument`
(`content_type="image"`) and indexing it into the same `np_web_pages`
index used for everything else — no changes needed to the BM25 query
path (`retrieval/lexical.py`) to pick them up.

Two signals are combined into `searchable_text`:
1. **OCR** (Tesseract, `nep+eng`) — text baked into the image itself
   (scanned notices, screenshots, infographics).
2. **Metadata from scraper/ETL**, when available — `alt_text`,
   `surrounding_context`, `parent_page_url`. Falls back gracefully if
   an image has no embedded text or no metadata.

Modules:
- `src/pgs_search/ingestion/image_indexer.py` — OCR + document-building
  (pure functions, no CLI, no OpenSearch client of its own — reuses
  `client/opensearch.py` and `config.settings`).
- `scripts/index_images.py` — CLI entry point, same pattern as
  `scripts/seed_demo_data.py`.

**Setup:**
```bash
pip install -e .            # pulls in pytesseract + Pillow from pyproject.toml
sudo apt-get install tesseract-ocr tesseract-ocr-nep
tesseract --list-langs      # confirm 'nep' is listed
```

**Run:**
```bash
python scripts/index_images.py --images-dir ./data/images
# with scraper/ETL metadata:
python scripts/index_images.py --images-dir ./data/images \
    --metadata-json ./data/image_metadata.json
```

---
