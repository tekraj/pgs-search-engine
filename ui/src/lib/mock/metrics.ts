import type { MetricPoint } from "@/lib/types";

// Sample data for the admin dashboard, shaped like the documented admin API
// (Section B of api/README.md) so each block can later be swapped for its real
// endpoint without touching the components:
//
//   getSummary()     → GET /api/v1/admin/dashboard/summary
//   getServices()    → GET /api/v1/admin/monitor/services
//   getNodes()       → GET /api/v1/admin/monitor/nodes
//   getDomains()     → GET /api/v1/admin/domains
//   getStorage()     → GET /api/v1/admin/storage/metrics
//   getErrorLogs()   → GET /api/v1/admin/logs/errors
//   getQuarantine()  → GET /api/v1/admin/security/quarantine
//
// Everything except the live chart and log stream is deterministic, so the
// server and the browser render the same thing.

const MINUTE = 60_000;

// ── Summary ──────────────────────────────────────────────────────────────────

export type SystemStatus = "HEALTHY" | "DEGRADED" | "DOWN";

export interface DashboardSummary {
  timestamp: string;
  system_status: SystemStatus;
  domains: { total_registered: number; active_crawling: number; completed: number; failed_or_blocked: number };
  links: { total_child_links_discovered: number; queued_for_crawl: number; filtered_by_bloom: number };
  storage: {
    total_raw_files_disk: number;
    unprocessed_files: number;
    processing_files: number;
    processed_files: number;
    total_storage_used_bytes: number;
    formatted_storage: string;
  };
  infrastructure: { k8s_active_nodes: number; temporal_worker_pods: number; spark_executors: number; kafka_brokers: number };
}

export function getSummary(now = Date.now()): DashboardSummary {
  return {
    timestamp: new Date(now).toISOString(),
    system_status: "DEGRADED",
    domains: { total_registered: 12450, active_crawling: 850, completed: 11100, failed_or_blocked: 500 },
    links: { total_child_links_discovered: 14_250_000, queued_for_crawl: 3_200_000, filtered_by_bloom: 9_800_000 },
    storage: {
      total_raw_files_disk: 4_850_000,
      unprocessed_files: 125_000,
      processing_files: 15_000,
      processed_files: 4_710_000,
      total_storage_used_bytes: 1_485_000_000_000,
      formatted_storage: "1.48 TB",
    },
    infrastructure: { k8s_active_nodes: 12, temporal_worker_pods: 48, spark_executors: 16, kafka_brokers: 3 },
  };
}

// ── Services ─────────────────────────────────────────────────────────────────

export type ServiceState = "UP" | "DEGRADED" | "DOWN";

export interface ServiceHealth {
  key: string;
  name: string;
  /** What the service does, in plain words. */
  role: string;
  status: ServiceState;
  /** The raw status the API returned, e.g. "GREEN" for OpenSearch. */
  raw_status: string;
  metrics: { label: string; value: string }[];
}

export function getServices(): ServiceHealth[] {
  return [
    {
      key: "temporal_orchestrator",
      name: "Temporal",
      role: "Runs crawl and ETL workflows",
      status: "UP",
      raw_status: "UP",
      metrics: [
        { label: "Latency", value: "3 ms" },
        { label: "Active workflows", value: "850" },
      ],
    },
    {
      key: "kafka_event_bus",
      name: "Kafka",
      role: "Hands crawled sites to ETL",
      status: "DEGRADED",
      raw_status: "UP",
      metrics: [
        { label: "Consumer lag", value: "4,200" },
        { label: "Consumers", value: "16" },
      ],
    },
    {
      key: "minio_dfs",
      name: "Object storage",
      role: "Raw crawled files",
      status: "UP",
      raw_status: "UP",
      metrics: [
        { label: "Latency", value: "12 ms" },
        { label: "Free", value: "18.5 TB" },
      ],
    },
    {
      key: "spark_streaming",
      name: "Spark",
      role: "Extracts, dedups and embeds",
      status: "UP",
      raw_status: "UP",
      metrics: [
        { label: "Active jobs", value: "4" },
        { label: "Batch time", value: "420 ms" },
      ],
    },
    {
      key: "redis_bloom_filter",
      name: "Bloom filter",
      role: "Skips already-seen links",
      status: "UP",
      raw_status: "UP",
      metrics: [
        { label: "Memory", value: "4.2 GB" },
        { label: "Keys", value: "14.25M" },
      ],
    },
    {
      key: "opensearch_cluster",
      name: "OpenSearch",
      role: "Search index",
      status: "UP",
      raw_status: "GREEN",
      metrics: [
        { label: "Documents", value: "4.71M" },
        { label: "Index size", value: "320.5 GB" },
      ],
    },
    {
      key: "clamav_scanner",
      name: "ClamAV",
      role: "Virus-scans every file",
      status: "UP",
      raw_status: "UP",
      metrics: [
        { label: "Version", value: "1.4.0" },
        { label: "Quarantined", value: "142" },
      ],
    },
  ];
}

// ── Nodes ────────────────────────────────────────────────────────────────────

export interface NodeMetrics {
  node_name: string;
  role: string;
  status: "Ready" | "NotReady";
  cpu_usage_percent: number;
  ram_usage: { used_gb: number; total_gb: number; percent: number };
  running_pods: number;
}

export function getNodes(): NodeMetrics[] {
  const node = (node_name: string, role: string, cpu: number, used: number, total: number, pods: number, ready = true) => ({
    node_name,
    role,
    status: ready ? ("Ready" as const) : ("NotReady" as const),
    cpu_usage_percent: cpu,
    ram_usage: { used_gb: used, total_gb: total, percent: Math.round((used / total) * 1000) / 10 },
    running_pods: pods,
  });
  return [
    node("worker-node-01", "Scraper fleet", 68.4, 48.2, 64, 8),
    node("worker-node-02", "Scraper fleet", 54.1, 39.0, 64, 8),
    node("spark-worker-01", "Spark executors", 81.7, 96.4, 128, 2),
    node("spark-worker-03", "Spark executors", 92.1, 112.0, 128, 2),
    node("search-node-01", "OpenSearch", 37.9, 41.5, 64, 3),
    node("control-plane-01", "Control plane", 22.3, 9.8, 16, 14),
  ];
}

// ── Domains ──────────────────────────────────────────────────────────────────

export type DomainStatus = "CRAWLING" | "PENDING" | "COMPLETED" | "FAILED" | "PAUSED";

export interface DomainRow {
  domain: string;
  category: "Government" | "Local government" | "Education" | "News" | "Organisation";
  status: DomainStatus;
  discovered_child_links: number;
  scraped_pages: number;
  failed_pages: number;
  last_crawled_at: string | null;
  rate_limit_per_sec: number;
}

const DOMAIN_SEEDS: Array<[string, DomainRow["category"], DomainStatus, number, number, number, number | null]> = [
  // domain, category, status, discovered, scraped, failed, minutes since last crawl
  ["mofaga.gov.np", "Government", "CRAWLING", 4520, 4100, 12, 10],
  ["psc.gov.np", "Government", "COMPLETED", 2310, 2298, 0, 95],
  ["moe.gov.np", "Government", "COMPLETED", 1840, 1802, 6, 180],
  ["mohp.gov.np", "Government", "CRAWLING", 3120, 1955, 31, 4],
  ["nrb.org.np", "Organisation", "COMPLETED", 5210, 5168, 2, 240],
  ["kathmandu.gov.np", "Local government", "CRAWLING", 2875, 2410, 18, 2],
  ["pokharamun.gov.np", "Local government", "COMPLETED", 1210, 1196, 3, 320],
  ["lalitpurmun.gov.np", "Local government", "PENDING", 0, 0, 0, null],
  ["bharatpurmun.gov.np", "Local government", "FAILED", 640, 212, 428, 55],
  ["tu.edu.np", "Education", "COMPLETED", 3980, 3911, 9, 410],
  ["ku.edu.np", "Education", "CRAWLING", 2240, 1630, 4, 6],
  ["pu.edu.np", "Education", "PENDING", 0, 0, 0, null],
  ["onlinekhabar.com", "News", "CRAWLING", 18_420, 16_905, 77, 1],
  ["ekantipur.com", "News", "COMPLETED", 21_300, 21_012, 41, 35],
  ["setopati.com", "News", "FAILED", 2100, 380, 1720, 70],
  ["ratopati.com", "News", "COMPLETED", 9450, 9401, 12, 140],
];

export function getDomains(now = Date.now()): DomainRow[] {
  return DOMAIN_SEEDS.map(([domain, category, status, discovered, scraped, failed, minutesAgo]) => ({
    domain,
    category,
    status,
    discovered_child_links: discovered,
    scraped_pages: scraped,
    failed_pages: failed,
    last_crawled_at: minutesAgo === null ? null : new Date(now - minutesAgo * MINUTE).toISOString(),
    rate_limit_per_sec: category === "News" ? 10 : 5,
  }));
}

// ── Storage ──────────────────────────────────────────────────────────────────

export interface StorageMetrics {
  unprocessed_queue: { count: number; size_gb: number; oldest_file_timestamp: string };
  processing_queue: { count: number; active_spark_executors: number };
  quarantine_store: { count: number; size_mb: number; latest_threat_detected: string };
}

export function getStorage(now = Date.now()): StorageMetrics {
  return {
    unprocessed_queue: { count: 125_000, size_gb: 42.5, oldest_file_timestamp: new Date(now - 80 * MINUTE).toISOString() },
    processing_queue: { count: 15_000, active_spark_executors: 16 },
    quarantine_store: { count: 142, size_mb: 520, latest_threat_detected: "Win.Trojan.Generic-998" },
  };
}

// ── Logs ─────────────────────────────────────────────────────────────────────

export type LogSeverity = "INFO" | "WARN" | "ERROR" | "FATAL";

export interface SystemLog {
  log_id: string;
  timestamp: string;
  service: string;
  severity: LogSeverity;
  domain?: string;
  url?: string;
  message: string;
}

type LogTemplate = Omit<SystemLog, "log_id" | "timestamp">;

const LOG_TEMPLATES: Record<LogSeverity, LogTemplate[]> = {
  INFO: [
    { service: "Scraper-Go-Worker-04", severity: "INFO", domain: "psc.gov.np", message: "Crawl finished: 2,298 pages, published site_crawl_completed" },
    { service: "ETL-Spark", severity: "INFO", message: "Batch of 100 sites processed, 41,208 documents written" },
    { service: "OpenSearch-Indexer", severity: "INFO", message: "Indexed 12,480 documents into pgs-documents" },
    { service: "Airflow-Scheduler", severity: "INFO", message: "scraper_crawl_schedule started CrawlDomainsWorkflow" },
    { service: "Search-API", severity: "INFO", message: "p95 query latency 118 ms over the last 5 minutes" },
  ],
  WARN: [
    { service: "Kafka-Consumer", severity: "WARN", message: "Consumer lag on scraped_files_topic above 4,000 events" },
    { service: "Scraper-Go-Worker-12", severity: "WARN", domain: "ku.edu.np", url: "https://ku.edu.np/notice", message: "Slow response (8.2 s), backing off to 2 requests/sec" },
    { service: "Spark-Executor-07", severity: "WARN", message: "Executor memory above 85% while embedding batch 4471" },
    { service: "ClamAV-Sidecar", severity: "WARN", domain: "setopati.com", url: "https://setopati.com/files/update.exe", message: "Malware detected: SCRIPT.Exploit.CVE-2023. File moved to quarantine" },
  ],
  ERROR: [
    { service: "Scraper-Go-Worker-12", severity: "ERROR", domain: "bharatpurmun.gov.np", url: "https://bharatpurmun.gov.np/data", message: "HTTP 503 Service Unavailable: rate limit exceeded by remote host" },
    { service: "ETL-Spark", severity: "ERROR", domain: "setopati.com", message: "PDF extraction failed: encrypted document, skipped" },
    { service: "OpenSearch-Indexer", severity: "ERROR", message: "Bulk request rejected (429), retrying in 30 s" },
  ],
  FATAL: [{ service: "Scraper-Go-Worker-09", severity: "FATAL", message: "Worker lost connection to Temporal, restarting pod" }],
};

const LOG_TIMELINE: Array<[LogSeverity, number, number]> = [
  // severity, template index, minutes ago
  ["INFO", 3, 58], ["INFO", 0, 54], ["WARN", 1, 49], ["INFO", 1, 44], ["ERROR", 0, 41],
  ["INFO", 2, 37], ["WARN", 3, 33], ["INFO", 4, 29], ["ERROR", 1, 26], ["WARN", 0, 22],
  ["INFO", 0, 18], ["FATAL", 0, 15], ["INFO", 3, 12], ["WARN", 2, 9], ["ERROR", 2, 6],
  ["INFO", 1, 4], ["INFO", 2, 2],
];

/** Recent log history (oldest first). */
export function getErrorLogs(now = Date.now()): SystemLog[] {
  return LOG_TIMELINE.map(([severity, index, minutesAgo], i) => ({
    log_id: `log_${99800 + i}`,
    timestamp: new Date(now - minutesAgo * MINUTE).toISOString(),
    ...LOG_TEMPLATES[severity][index],
  }));
}

let liveLogCounter = 0;

/** A new random log line for the live stream (browser only). */
export function generateLiveLog(): SystemLog {
  const r = Math.random();
  const severity: LogSeverity = r < 0.7 ? "INFO" : r < 0.9 ? "WARN" : r < 0.985 ? "ERROR" : "FATAL";
  const templates = LOG_TEMPLATES[severity];
  liveLogCounter += 1;
  return {
    log_id: `live_${Date.now().toString(36)}_${liveLogCounter}`,
    timestamp: new Date().toISOString(),
    ...templates[Math.floor(Math.random() * templates.length)],
  };
}

// ── Quarantine ───────────────────────────────────────────────────────────────

export interface QuarantinedFile {
  file_id: string;
  file_name: string;
  domain: string;
  threat: string;
  size_kb: number;
  detected_at: string;
}

export function getQuarantine(now = Date.now()): QuarantinedFile[] {
  return [
    { file_id: "q_142", file_name: "update.exe", domain: "setopati.com", threat: "SCRIPT.Exploit.CVE-2023", size_kb: 2310, detected_at: new Date(now - 33 * MINUTE).toISOString() },
    { file_id: "q_141", file_name: "notice_2083.docm", domain: "bharatpurmun.gov.np", threat: "Doc.Downloader.Emotet-9", size_kb: 184, detected_at: new Date(now - 190 * MINUTE).toISOString() },
    { file_id: "q_140", file_name: "setup_installer.zip", domain: "ku.edu.np", threat: "Win.Trojan.Generic-998", size_kb: 8740, detected_at: new Date(now - 420 * MINUTE).toISOString() },
    { file_id: "q_139", file_name: "result.pdf.js", domain: "pu.edu.np", threat: "JS.Downloader.Agent-31", size_kb: 46, detected_at: new Date(now - 26 * 60 * MINUTE).toISOString() },
  ];
}

// ── Live system load (browser only) ──────────────────────────────────────────

export function generateMetricSeries(points = 30, stepMs = 2 * MINUTE): MetricPoint[] {
  const now = Date.now();
  let cpu = 52;
  let ram = 61;
  let qps = 140;
  let latency = 85;

  return Array.from({ length: points }).map((_, i) => {
    cpu = clamp(cpu + (Math.random() - 0.5) * 12, 15, 92);
    ram = clamp(ram + (Math.random() - 0.5) * 6, 30, 88);
    qps = clamp(qps + (Math.random() - 0.5) * 40, 60, 320);
    latency = clamp(latency + (Math.random() - 0.5) * 20, 40, 260);
    return {
      time: new Date(now - (points - 1 - i) * stepMs).toISOString(),
      cpu: Math.round(cpu),
      ram: Math.round(ram),
      queriesPerSec: Math.round(qps),
      latencyMs: Math.round(latency),
    };
  });
}

export function nextMetricPoint(last: MetricPoint): MetricPoint {
  return {
    time: new Date().toISOString(),
    cpu: Math.round(clamp(last.cpu + (Math.random() - 0.5) * 12, 15, 92)),
    ram: Math.round(clamp(last.ram + (Math.random() - 0.5) * 6, 30, 88)),
    queriesPerSec: Math.round(clamp(last.queriesPerSec + (Math.random() - 0.5) * 40, 60, 320)),
    latencyMs: Math.round(clamp(last.latencyMs + (Math.random() - 0.5) * 20, 40, 260)),
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
