export type Status = "healthy" | "degraded" | "down" | "unknown";

export interface ServiceCheck {
  name: string;
  group: string;
  target: string;
  status: Status;
  latency_ms: number | null;
  detail: string | null;
  checked_at: string;
}

export interface NodeStatus {
  node_id: string;
  hostname: string;
  role: string;
  ip_address: string | null;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  load_1m: number;
  cpu_count: number;
  uptime_seconds: number;
  status: Status;
  status_reason: string | null;
  last_seen: string;
  age_seconds: number;
}

export interface Overview {
  generated_at: string;
  summary: {
    overall: Status;
    services_total: number;
    services_healthy: number;
    services_degraded: number;
    services_down: number;
    nodes_total: number;
    nodes_healthy: number;
    nodes_degraded: number;
    nodes_down: number;
  };
  services: ServiceCheck[];
  nodes: NodeStatus[];
}

export class AuthError extends Error {}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchOverview(
  token: string,
  signal?: AbortSignal,
): Promise<Overview> {
  const res = await fetch(`${API_BASE}/api/v1/admin/monitoring/overview`, {
    headers: { "X-Admin-Token": token },
    cache: "no-store",
    signal,
  });
  if (res.status === 401) throw new AuthError("That token was not accepted.");
  if (res.status === 503)
    throw new AuthError("The server has no admin token configured.");
  if (!res.ok) throw new Error(`The API returned ${res.status}.`);
  return (await res.json()) as Overview;
}

const SEVERITY: Record<Status, number> = {
  healthy: 0,
  unknown: 1,
  degraded: 2,
  down: 3,
};

export function worst(statuses: Status[]): Status {
  if (statuses.length === 0) return "unknown";
  return statuses.reduce((a, b) => (SEVERITY[b] > SEVERITY[a] ? b : a));
}

export function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export function formatAge(seconds: number): string {
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  return `${Math.round(seconds / 3600)}h ago`;
}