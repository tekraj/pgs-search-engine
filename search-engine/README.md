bm25-opensearch-vectorsearch
# System Architecture & Technical Design Specification

## Bilingual Search Engine Core with Spatial Intelligence (Internal Service)


## 1. Executive Summary

This document details the architecture for the **Search Engine Core**, a highly scalable, bilingual search engine covering the Nepalese web ecosystem.

**Crucially, this Search Engine exposes no public APIs.** It operates entirely as an internal, backend microservice within a private virtual network. It receives queries and streams results exclusively via high-performance **gRPC** protocols to a dedicated API Gateway layer.

The core pipeline features **Geo-Spatial & Administrative Entity Intelligence**, enabling it to process both standard lexical queries and strict region-bounded administrative searches over its OpenSearch indices.



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


# PGS Search Engine Service

## gRPC Search Service

Rabin's gRPC layer owns communication between the external FastAPI API service and the
internal Search Engine service. It exposes `SearchService.ExecuteSearch`, converts protobuf
requests into a typed adapter input, calls `SearchPipelineAdapter`, and returns protobuf
`SearchResponse` messages.

Architecture flow:

```text
Frontend
  -> HTTP/REST
FastAPI Gateway
  -> gRPC
Search Engine SearchService
  -> SearchPipelineAdapter
  -> gRPC SearchResponse
FastAPI Gateway
  -> JSON response
Frontend
```

The service listens on port `50051` by default. Override the bind address with
`SEARCH_GRPC_HOST` and `SEARCH_GRPC_PORT`.

Generate protobuf code:

```bash
PYTHONPATH=search-engine/src search-engine/.venv/bin/python -m grpc_tools.protoc \
  -Isearch-engine/proto \
  --python_out=search-engine/src/pgs_search/grpc/generated \
  --grpc_python_out=search-engine/src/pgs_search/grpc/generated \
  search-engine/proto/search.proto
```

If `search_pb2_grpc.py` generates `import search_pb2 as search__pb2`, change it to:

```python
from . import search_pb2 as search__pb2
```

Start the gRPC server:

```bash
PYTHONPATH=search-engine/src python -m pgs_search.grpc.server
```

Run the manual client:

```bash
PYTHONPATH=search-engine/src python search-engine/scripts/test_grpc_client.py
```

Example request:

```python
SearchRequest(
    query="पोखरा बजेट",
    province_code="P4",
    district_code="D39",
    language="ne",
    page=1,
    limit=10,
)
```

`SearchPipelineAdapter` is a temporary integration stub. It returns one deterministic mock
result until the BM25, vector search, embeddings, and LightGBM reranking pipeline is ready to
be wired in search-engine
