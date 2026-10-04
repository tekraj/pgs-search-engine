# PGS Search Engine — Docker Deployment Guide

> **Who this is for:** anyone on the team, including people with no Docker
> experience. It explains *what* we set up, *why* we made each decision, and
> *how* to run, debug, and explain it.

---

## 1. The big picture

PGS Search Engine is several small programs ("services") that talk to each
other over the network, plus some shared infrastructure (database, message
queue, search index). Each one runs in its own isolated container.

Think of containers like lunch boxes: each service gets its own box with
exactly the ingredients it needs, and they pass notes through a shared
lunch table (the Docker network).

```
┌─────────┐   REST    ┌───────┐   gRPC    ┌─────────────────┐   ┌───────────┐
│   UI    │ ────────▶ │  api  │ ────────▶ │ search-engine   │ ─▶ │ OpenSearch│
│ :3000   │           │ :8000 │           │     :50051      │   └───────────┘
└─────────┘           └───────┘           └─────────────────┘
                                                  │           ┌──────────────┐
                                                  └─────────▶ │  PostgreSQL  │
┌─────────┐  Kafka   ┌────────┐           ┌─────────────────┤  :5432       ├─┐
│scraper  │ ───────▶ │ Kafka  │ ◀──────── │ etl-consumer    │  (+PostGIS,  │ │
│(Go)     │          │  :29092│           │ (Python)        │   pgvector)  │ │
└─────────┘          └────────┘           └─────────────────┘                │
       │                  ▲                                                  │
       │                  │ Kafka :29092                                     │
┌──────┴──────┐   ┌──────┴───────┐    Airflow reads/schedules                │
│  Temporal   │   │   ETL jobs   │ ──────────────────────────────────────────┘
│   :7233     │   │  (Spark)     │
└─────────────┘   └──────────────┘
```

---

## 2. What we created or fixed

| Change | File | Why |
| --- | --- | --- |
| **New** master orchestrator | `docker-compose.yml` | The repo had per-service compose fragments but no single file to start everything. It defines 20 services, the shared network, volumes, ports, env vars, and startup order. |
| **New** env template | `.env.example` | All credentials/settings live in one place; `docker compose` reads `.env` automatically. |
| **Fixed** stale UI lockfile | `ui/package-lock.json` | `package.json` had 7 new dependencies but the lock file was never updated, so `npm ci` failed inside the UI Docker build. Regenerated. |
| **Gated** scraper worker | `docker-compose.yml` | `scraper/go.mod` is out of sync with its code (missing Temporal/Prometheus deps and packages), so its build fails. It now sits behind an opt-in profile so the rest of the stack starts. |

Everything else (per-service Dockerfiles, `.dockerignore` files) **already
existed and was kept** — we verified each one matches how the service really
starts.

---

## 3. The services, in plain English

### User-facing
- **ui** — the website (Next.js). What users open in a browser. Port **3000**.
- **api** — the public REST API (FastAPI). The UI talks to it. Port **8000**.

### Brains
- **search-engine** — the actual search logic. A Python service exposing
  **gRPC** on port 50051 (gRPC is a faster, stricter cousin of REST used
  between internal services).

### Data & infrastructure
- **postgres** — the main database (PostgreSQL 16) extended with:
  - **pgvector** — stores AI "embeddings" for semantic search.
  - **PostGIS** — stores map/geography shapes (Nepal provinces etc.).
  Port **5432**.
- **kafka** — a durable message queue. Producers (scraper) drop messages,
  consumers (ETL) pick them up at their own pace. No ZooKeeper needed
  (KRaft mode). Ports **9092** (host) / **29092** (internal).
- **opensearch** — the search index engine the search-engine queries. Port **9200**; dashboards on **5601**.
- **temporal** — scheduler the Go scraper worker uses for retries/queues. Port **7233**.

### Workers & pipelines
- **scraper** (Go, profile `crawler`) — crawls websites, publishes results to Kafka or Postgres.
- **etl-consumer** — reads documents off Kafka, validates them, records a receipt in a local SQLite file.
- **ETL Spark** (`etl-spark-test`) — PySpark transformation smoke test.
- **Airflow** (`airflow-webserver/-scheduler/-worker/-init`) — web UI + scheduler for scheduled batch jobs at http://localhost:8080 (login `airflow`/`airflow`).

### One-shot setup jobs (run once, then exit)
- **db-migrate** — creates/updates the database schema (Alembic).
- **db-role-passwords** — sets each service's DB password.
- **db-seed** — loads reference geography data.

These exist so the app never starts against a half-prepared database.

---

## 4. Key decisions and why

1. **One network (`pgs-network`)** — every container can reach every other by
   service name (`postgres`, `kafka`, `search-engine`...). No more `localhost`
   headaches: inside containers, `localhost` means *the same container*.
2. **Kafka advertised listeners** — this is the #1 Docker-Kafka gotcha:
   - Host machine clients → `localhost:9092`
   - Services inside the network → `kafka:29092`
   `KAFKA_ADVERTISED_LISTENERS` enforces this, so both `kafka-python` (ETL)
   and Go `kafka-go` (scraper) can connect.
3. **KRaft instead of ZooKeeper** — one less container to run and debug.
4. **Multi-stage Dockerfiles** — build in a big image ( compilers, toolchains ),
   ship a tiny one (Alpine/slim/distroless). Verified per service:
   - Go services: `golang` build → distroless/static runtime
   - UI: node build → Next.js standalone server
   - Python services: venv build → slim runtime
5. **Startup order via `depends_on`** with healthchecks: postgres → db-migrate
   → db-role-passwords → api; kafka → etl-consumer/scraper; airflow-init →
   webserver/scheduler/worker.
6. **Secrets via `.env`** — no passwords hardcoded in the compose file.
7. **`.dockerignore` files** — keep `node_modules`, `.venv`, `__pycache__`,
   `.git`, and test folders out of build contexts (faster builds, smaller images).

---

## 5. How to run everything

```powershell
# 1. One time: create your local env file
cp .env.example .env

# 2. Build and start the whole stack
docker compose up --build -d

# 3. Watch logs (Ctrl+C to stop watching)
docker compose logs -f

# Stop everything (keep your data)
docker compose down

# Stop and DELETE all data volumes
docker compose down -v
```

Then open:
| What | URL | Login |
|---|---|---|
| UI | http://localhost:3000 | — |
| API | http://localhost:8000 | — |
| Airflow | http://localhost:8080 | airflow / airflow |
| OpenSearch Dashboards | http://localhost:5601 | — |

To include the Go scraper worker as well (only after fixing its `go.mod`):

```powershell
docker compose --profile crawler up --build -d
```

---

## 6. Troubleshooting cheatsheet

| Symptom | Likely cause | Fix |
|---|---|---|
| `pull access denied for pgs-*` | Ran `up` without `--build` | Use `docker compose up --build -d` |
| Empty `PGS_*_PASSWORD` warnings | `.env` missing | `cp .env.example .env` |
| `npm ci` "out of sync" errors | Stale `package-lock.json` | Regenerate (already fixed): see `git log -p ui/package-lock.json` |
| Kafka clients can't connect | Wrong listener (`localhost` inside a container) | Use `kafka:29092` between containers, `localhost:9092` on the host |
| Airflow webserver 502/unhealthy | Still initializing | Wait ~30–60s; check `docker compose logs airflow-init` |
| `scraper` build fails | `scraper/go.mod` out of sync | Run `cd scraper; go mod tidy`, or skip with the default profile |

---

## 7. For your report / presentation

One-paragraph version you can paste:

> "We containerized the PGS Search Engine monorepo with Docker. Each service
> (FastAPI gateway, Next.js UI, Go crawler, Python/Spark ETL, OpenSearch,
> PostgreSQL+PostGIS+pgvector, Kafka, Temporal, Airflow) runs in its own
> container from a tailored multi-stage Dockerfile. A root `docker-compose.yml`
> orchestrates 20 services on a shared bridge network with healthchecks,
> dependency ordering, persistent volumes, and KRaft-mode Kafka with
> per-client advertised listeners. Database schema is created by automated
> Alembic migration jobs before APIs start. Everything builds with
> `docker compose up --build -d`. We also fixed a stale npm lockfile that
> broke the UI build and isolated the scraper behind a profile pending a
> `go.mod` repair."

---

## 8. Repo map of the Docker files

```
pgs-search-engine/
├── docker-compose.yml        # ← the master orchestrator (NEW)
├── .env.example              # ← environment template (NEW)
├── docker/postgres/set-role-passwords.sql
├── api/Dockerfile            # FastAPI, multi-stage slim
├── ui/Dockerfile             # Next.js standalone, multi-stage node
├── scraper/Dockerfile        # Go → distroless static
├── search-engine/Dockerfile  # CPU torch, gRPC :50051
├── ETL/Dockerfile            # Airflow + PySpark + kafka-python
├── ETL/spark/Dockerfile      # standalone Spark test image
├── database/Dockerfile       # pg 16 + pgvector + PostGIS
├── database/migrate.Dockerfile  # alembic upgrade head image
└── **/.dockerignore          # keep build contexts small
```
