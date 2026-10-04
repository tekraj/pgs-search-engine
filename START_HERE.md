# PGS Search Engine — Start Here (for everyone)

> You don't need to understand Docker to run this. Just follow Steps 1-5 exactly.
> Time needed: ~30-60 minutes the first time (mostly waiting for downloads).

## What is this?

One search website + all its helpers (database, search index, message queue) running together on your computer. Each helper runs in its own box called a **container**. You start them all with one command.

## What you need

1. **Windows 10/11** (or Mac/Linux — commands are the same, use Terminal instead of PowerShell)
2. **Docker Desktop** installed and running (whale icon in taskbar). Download: https://www.docker.com/products/docker-desktop/
3. **20 GB free disk** — search software is big (OpenSearch alone is ~1 GB download, whole project ~12-15 GB)
4. **8 GB RAM minimum** — this runs 15+ things at once
5. **Internet** for the first start (to download images + AI models)
6. This project folder: `pgs-search-engine`

## Step 1 — Open a terminal in the project folder

In Windows Explorer, open the `pgs-search-engine` folder, right-click empty space → **Open in Terminal**, or in PowerShell:

```powershell
cd "C:\Users\john\Music\Tekraj sir\pgs-search-engine"
```

## Step 2 — Create your settings file (once only)

```powershell
Copy-Item .env.example .env
```

If it says the file already exists, skip — you already have `.env`. You never need to edit it for a demo.

## Step 3 — Start everything

```powershell
docker compose up --build -d
```

What this means:

- `up` = start everything
- `--build` = build our own parts (website, API, search). Always include it the first time.
- `-d` = run quietly in the background (no scrolling text). Leave `-d` off only if you want to watch logs.

First run downloads a lot. **This is normal:**

- `opensearch: 1.07 GB` — yes, really that big, it's a full search engine + Java
- `hello-world: few KB` — tiny test image, ignore it
- `search-engine` then downloads AI models (`nllb-200`, `all-MiniLM`) — 10-20 min on first start

If you see `TLS handshake timeout` / `failed to fetch oauth token`: your internet/VPN blocked Docker Hub. Disconnect VPN, retry the same command, or run `docker pull hello-world` to test.

## Step 4 — Wait until it's ready (important)

Check status:

```powershell
docker compose ps
```

Wait until you see `running` / `healthy` for `postgres`, `kafka`, `opensearch`, `api`, `ui`. Then wait **5-15 more minutes** for `search-engine` — watch it with:

```powershell
docker compose logs search-engine --tail 20 -f
```

You're ready when you see `Translation model ready` + `Embedding model ready` (or `gRPC :50051`). Press `Ctrl+C` to stop watching logs.

## Step 5 — Open it

| What | Address | Login |
|---|---|---|
| Search website (UI) | http://localhost:3000 | — |
| API | http://localhost:8000/ | — |
| Airflow (scheduled jobs) | http://localhost:8080 | `airflow` / `airflow` |
| OpenSearch Dashboard | http://localhost:5601 | — |

If the website loads but search returns nothing yet, `search-engine` is still downloading models — wait and retry.

## Everyday commands

```powershell
docker compose ps              # are things running? (the 1/1 table you asked about)
docker compose logs -f         # watch live logs (all services)
docker compose logs api -f     # watch only one service (api, ui, search-engine, kafka, postgres...)
docker compose down            # stop everything, keep your data
docker compose down -v          # stop + DELETE all data (fresh start, you will re-download)
docker compose up --build -d   # start again after a stop
```

Why `up` shows scrolling text and no `1/1` table: plain `docker compose up` runs in **foreground** (attached, shows logs). Adding `-d` runs **detached**, then `docker compose ps` gives you the clean status table.

## Scary messages you can ignore

| You see | What it really is |
|---|---|
| `api ... GET /health 404` | Normal. The API (`api/main.py`) only has `GET /`, there is no `/health` endpoint yet. `GET /` returns `200 OK`. |
| `temporal ... context deadline exceeded` / `Failed to poll for task` | Happens when your laptop is overloaded. It retries by itself. |
| `airflow-scheduler ... could not translate host name airflow-postgres` | Temporary DNS hiccup under load. It retries. If persistent, restart: `docker compose restart airflow-scheduler` |
| `opensearch ... Security plugin disabled`, `performance-analyzer ... No such file`, `JvmGcMonitor overhead`, `FsHealth took 35s` | Warnings from a heavy single-node OpenSearch on WSL2. Normal for a demo. |
| `kafka ... heartbeat timeout / rebalancing / unloaded group` | Kafka reacting to the same host stall above. It re-elects and recovers alone. |
| `search-engine ... Can't load facebook/nllb-200 ... pytorch_model.bin / Xet CAS error` | Transient HuggingFace download failure. Container restarts and resumes. Only worry if it loops for >1 hour. |

Real problems are: `port already in use` (close the other program or change the port in `.env`), `no space left on device` (free disk / `docker system prune`), or a service stuck in `Restarting (1)` for 30+ min — then run `docker compose logs <name> --tail 50` and share that output.

## To show someone else

1. They install Docker Desktop.
2. They copy this folder + run Steps 1-5. No code editing needed.
3. Send them the 4 URLs above.

To include the Go crawler (optional, currently gated): `docker compose --profile crawler up --build -d` — only after `scraper/go.mod` is fixed (`cd scraper; go mod tidy`).

## If it breaks, do this in order

1. `docker compose ps` — which service is not `running`?
2. `docker compose logs <that-name> --tail 50` — last 50 lines tell the story
3. Retry: `docker compose up --build -d`
4. Nuclear: `docker compose down -v` then Step 3 again (re-downloads everything)
