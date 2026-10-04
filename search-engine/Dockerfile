# syntax=docker/dockerfile:1
#
# Search Engine Core: the internal gRPC SearchService on :50051.
# Build context: the repository root (needs search-engine/ and the shared database/
# package).
#
# The code runs from its source layout (/app is search-engine/): it finds
# models/lightgbm_reranker.pkl relative to its own files and imports the top-level
# vector_search/ and fusion/ packages from that root, exactly as
# `PYTHONPATH=search-engine/src python -m pgs_search.grpc.server` does locally. So only
# its dependencies are installed; the project is put on PYTHONPATH, not pip-installed.

ARG PYTHON_VERSION=3.11

FROM python:${PYTHON_VERSION}-slim-trixie AS build
# CPU-only PyTorch: the code runs on CPU; the default PyPI wheel pulls in several GB of CUDA libraries.
ARG TORCH_VERSION=2.14.1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY search-engine/pyproject.toml /src/search-engine/pyproject.toml
COPY database/constraints.txt database/pyproject.toml database/README.md /src/database/
COPY database/src /src/database/src
# Read dependency list from search-engine/pyproject.toml so pyproject.toml stays single source of truth
RUN --mount=type=cache,target=/root/.cache/pip \
    python -c "import tomllib; deps = tomllib.load(open('/src/search-engine/pyproject.toml', 'rb'))['project']['dependencies']; print('\n'.join(deps))" \
        > /tmp/search-engine-requirements.txt \
    && pip install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH_VERSION}+cpu" \
        --requirement /tmp/search-engine-requirements.txt \
        --constraint /src/database/constraints.txt \
        "/src/database[postgres]"

FROM python:${PYTHON_VERSION}-slim-trixie
# LightGBM wheel links against system OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/home/app/.cache/huggingface
# Hugging Face models (NLLB-200, MiniLM) download into HF_HOME, backed with a volume.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app \
        --shell /usr/sbin/nologin app \
    && mkdir -p "${HF_HOME}" \
    && chown -R app:app /home/app/.cache
COPY --from=build /opt/venv /opt/venv

WORKDIR /app
COPY search-engine/ ./

USER 10001:10001
EXPOSE 50051
# Ready once the gRPC port binds
HEALTHCHECK --interval=30s --timeout=5s --start-period=30m --start-interval=15s --retries=3 \
    CMD ["python", "-c", "import socket; socket.create_connection(('127.0.0.1', 50051), timeout=3).close()"]
CMD ["python", "-m", "pgs_search.grpc.server"]
