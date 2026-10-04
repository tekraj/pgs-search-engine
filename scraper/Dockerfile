# syntax=docker/dockerfile:1
#
# Go crawler: cmd/worker, the Temporal worker that fetches pages and writes crawled
# documents to NDJSON / PostgreSQL / Kafka (--storage). Flags can be configured through
# environment variables (e.g. KAFKA_BROKERS, TEMPORAL_ADDRESS, etc.).
# Build context: scraper/

ARG GO_VERSION=1.23

FROM golang:${GO_VERSION}-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download
COPY . .
# Pure-Go dependencies: build static binary (CGO_ENABLED=0) for distroless static base
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/worker ./cmd/worker \
    && mkdir -p /out/data/output

# distroless/static contains CA certificates for HTTPS crawling, tzdata, and unprivileged user (65532)
FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=build /out/worker /app/worker
COPY --from=build --chown=65532:65532 /out/data /app/data
EXPOSE 9090
ENTRYPOINT ["/app/worker"]
