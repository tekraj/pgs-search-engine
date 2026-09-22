# Database (`pgs-db`)

We design and manage the PostgreSQL database that the scraper, ETL, search engine and API all share.

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

## 3. How data is organised

We use three layers:

| Layer | Meaning | Main tables |
|---|---|---|
| **Bronze** | Raw: a record of every downloaded file, unchanged | `raw_files`, `quarantined_files` |
| **Silver** | Clean: one record per page, duplicates removed, location tagged | `pages`, `page_geo_tags`, `page_contacts` |
| **Gold** | Ready to use: summaries for the map and dashboard | `district_stats`, `domain_stats` |

Plus **reference tables** that everything links to:

- `provinces` (7), `districts` (77), `local_bodies` (753)
- `domains`: the list of websites to crawl
- `admin_users`

## 4. Planned tables (draft)

> Column lists are a draft and may change after we get your answers.

| Table | Key columns | Written by | Read by |
|---|---|---|---|
| `provinces` | code, name_en, name_ne | Database group | API, UI |
| `districts` | code, province_code, name_en, name_ne | Database group | API, UI |
| `local_bodies` | id, district_code, type, name_en, name_ne, website, phone, email | Database group | ETL, API |
| `domains` | domain, category, status, priority, rate_limit, local_body_id | API (admin) | Scraper, API |
| `raw_files` | url, domain_id, minio_path, file_sha256, content_type, http_status, scraped_at, status | Scraper | ETL, API |
| `quarantined_files` | url, domain_id, threat_name, file_sha256, detected_at | Scraper / ClamAV | API |
| `pages` | raw_file_id, title, description, language, published_date, type, duplicate_of | ETL | Search, API |
| `page_geo_tags` | page_id, local_body_id, ward_number | ETL | Search, API |
| `page_contacts` | page_id, type (email/phone/social), value | ETL | API |
| `district_stats` | local_body_id, page_count, updated_at | ETL (batch) | API, UI map |
| `domain_stats` | domain_id, pages_scraped, pages_failed | ETL (batch) | API, admin UI |
| `error_logs` | time, service, severity, url, message | All services | API |
| `admin_users` | username, password_hash, role | API | API |

## 5. Rules everyone should follow

1. **Don't create or change tables yourself.** Ask the Database group. All changes go through migrations (Alembic) so everyone stays in sync.
2. **Never store file contents in PostgreSQL.** Store the MinIO path instead.
3. **All times in UTC.**
4. **Use the fixed status values** we publish, e.g. `PENDING`, `CRAWLING`, `DONE`, `FAILED`.
5. **Python services** can use our package: `pip install -e ./database`, then `import pgs_db`.
6. **Non-Python services** (Go scraper, Spark) write to the same tables using the column list we publish.

