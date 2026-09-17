# Go Distributed Web Scraper & ETL Pipeline Architecture


## 1. Domain Discovery & Seed Registration

Before scraping begins, all seed target domains must be enumerated, validated, and registered into the system database.

### 1.1 Primary Institutional Registries

* **Government & Local Bodies:** Central gateway (`nepal.gov.np`), MoFAGA 753 local bodies directory (`mofaga.gov.np`), Supreme/District Courts (`supremecourt.gov.np`), PPMO procurement registry (`ppmo.gov.np`).
* **Education:** University Grants Commission (`ugcnepal.edu.np`), CEHRD & NEB secondary schools/colleges (`cehrd.gov.np`, `neb.gov.np`), CTEVT technical institutes (`ctevt.org.np`).
* **Media & News:** Press Council Nepal online news database (`presscouncilnepal.gov.np`), Department of Information & Broadcasting (`doib.gov.np`).
* **Finance & Banking:** Nepal Rastra Bank Class A–D directory (`nrb.org.np`), SEBON & NEPSE capital market entities (`sebon.gov.np`, `nepalstock.com.np`), Nepal Insurance Authority (`nia.gov.np`).
* **Non-Profits & NGOs:** Social Welfare Council registry (`swc.org.np`).
* **Commercial & Business:** Office of the Company Registrar (`ocr.gov.np`), commercial directories (`nepalyp.com`, `yellowpagesnepal.com`).

### 1.2 Passive Domain Enumeration

* **Certificate Transparency (CT) Logs:** Query public SSL databases (`crt.sh`) for domain patterns: `%.gov.np`, `%.edu.np`, `%.com.np`, `%.org.np`.
* **Wayback Machine CDX API:** Query historical open index logs using `[http://web.archive.org/cdx/search/cdx?url=*.np/*&output=json&fl=original&collapse=urlkey](http://web.archive.org/cdx/search/cdx?url=*.np/*&output=json&fl=original&collapse=urlkey)`.

---

## 2. Distributed Scraper Execution & Recursive Traversal

The scraper handles network I/O, full internal link graph discovery, rate limiting, and raw file writing to storage.

### 2.1 Recursive Internal Link Traversal Rule

* **Complete Internal Discovery:** The scraper starts at the target domain's homepage (or sitemap URLs), extracts all hyperlinked URLs (`<a>` tags), and recursively visits every internal link belonging to that domain.
* **Continuous Loop:** Every newly discovered internal URL is added back to the domain's crawl queue. This process repeats recursively until **all accessible subpages of the domain have been fully scraped**.
* **Strict Domain Boundary:** The scraper stays locked strictly within the target domain (`*.example.gov.np`). Outbound links pointing to third-party domains are extracted and recorded in metadata, but are **never followed** by that domain's workflow.

### 2.2 Compliance & Rate Control

* **Crawl Politeness & Rate Limiting:** Enforce per-domain request throttles, delay intervals, and concurrent request limits across worker containers to prevent IP bans.
* **Robots & Sitemap Evaluation:**
1. Parse `sitemap.xml` (if available) to pre-seed the internal link queue.
2. Respect `robots.txt` disallow directives.
3. If both are missing, proceed with full recursive crawling of all internal URLs.



### 2.3 Per-Page Extraction Scope

For **every page** visited during the recursive crawl:

* **Page Metadata:** `<title>`, `<meta description>`, `<meta keywords>`, canonical tags, OpenGraph data.
* **Contact & Social Info:** Phone numbers, email addresses, physical addresses, social media links (Facebook, Twitter/X, LinkedIn, YouTube).
* **Page Content:** Raw HTML content, extracted main body text, inline image references, video links.
* **Documents & PDFs:** PDF binary downloads and office documents, routed directly to storage.

---

## 3. Storage Protocol & Self-Contained File Format

The scraper does **not** write raw page content directly to the SQL database. It writes each scraped page as an independent payload into the **Distributed File System (DFS)** (e.g., MinIO/S3).

### 3.1 DFS File Payload Contract

Each saved file contains both the extracted page metadata and the raw content body so the ETL can process it asynchronously without external state lookups.

```json
{
  "storage_metadata": {
    "website_name": "Ministry of Federal Affairs",
    "target_domain": "mofaga.gov.np",
    "page_url": "https://mofaga.gov.np/notice/detail/456",
    "scraped_at": "2026-09-16T22:25:00Z",
    "content_type": "text/html",
    "http_status": 200,
    "crawl_depth": 3
  },
  "extracted_metadata": {
    "title": "...",
    "description": "...",
    "keywords": ["nepal", "local government"],
    "contact_info": {
      "emails": ["info@mofaga.gov.np"],
      "phones": ["+977-1-4200000"],
      "address": "Singha Durbar, Kathmandu"
    },
    "social_links": [
      "https://facebook.com/mofaga"
    ],
    "discovered_internal_links": [
      "https://mofaga.gov.np/notice/detail/457",
      "https://mofaga.gov.np/about/team"
    ],
    "discovered_external_links": [
      "https://nepal.gov.np"
    ]
  },
  "raw_payload": {
    "file_extension": "html",
    "content_encoding": "utf-8",
    "data": "PGh0bWw+... (Base64 encoded or raw string)"
  }
}

```

* **Documents & PDFs:** Binary files are uploaded under a `/documents/` storage path. The document's source page URL, storage path, and file hash are written into the document's metadata wrapper.

---

## 4. Orchestration & Downstream ETL Handoff

* **Temporal Workflows:** Each domain run executes as a **Temporal Workflow**, coordinating recursive crawl tasks across a cluster of Go worker containers.
* **ETL Handoff Sequence:**
1. **Scraper Worker:** Fetches page $\rightarrow$ Extracts subpage URLs and adds unvisited ones to crawl queue $\rightarrow$ Writes metadata + payload file to DFS $\rightarrow$ Emits completion signal (Kafka/RabbitMQ/Temporal Signal).
2. **ETL Worker:** Picks up completion signal $\rightarrow$ Reads raw file from DFS $\rightarrow$ Performs text parsing, PDF text extraction, duplicate checks, and NLP $\rightarrow$ Upserts clean structured data into primary database.