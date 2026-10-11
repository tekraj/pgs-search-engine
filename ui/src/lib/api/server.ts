// Server-side calls from the Next.js server to the FastAPI gateway (API_INTERNAL_URL).
// Only imported by server components and route handlers: the browser never talks to
// the API through this module.
import { serverEnv } from "@/lib/env";

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: string };

interface ApiOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  token?: string;
  /** The browser's address, passed on as X-Real-IP / X-Forwarded-For so the API's login throttle counts the right client. */
  clientIp?: string;
  body?: unknown;
  searchParams?: Record<string, string | number | undefined>;
}

/**
 * The caller's address, from the header CLIENT_IP_SOURCE names (the one our proxy sets or
 * overwrites; any other is client-controlled). Pass it as `clientIp`.
 */
export function clientIpOf(request: Request): string | undefined {
  const source = serverEnv().clientIpSource;
  if (source === "x-real-ip") return request.headers.get("x-real-ip")?.trim() || undefined;
  if (source === "x-forwarded-for") {
    // One proxy hop appends the address it saw as the last entry.
    return request.headers.get("x-forwarded-for")?.split(",").at(-1)?.trim() || undefined;
  }
  return undefined;
}

/** For endpoints that answer 204 No Content: the body is null. */
export const isEmpty = (value: unknown): value is null => value === null;

/** Call the API with a timeout. Never throws: network failures come back as status 0. */
export async function apiFetch<T>(
  path: string,
  validate: (value: unknown) => value is T,
  options: ApiOptions = {},
): Promise<ApiResult<T>> {
  const env = serverEnv();
  const url = new URL(`${env.apiInternalUrl}${path}`);
  for (const [name, value] of Object.entries(options.searchParams ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(name, String(value));
  }
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.clientIp) {
    // Both, so the API finds it whichever API_CLIENT_IP_SOURCE it trusts.
    headers["X-Real-IP"] = options.clientIp;
    headers["X-Forwarded-For"] = options.clientIp;
  }
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      cache: "no-store",
      signal: AbortSignal.timeout(env.apiTimeoutMs),
    });
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === "TimeoutError";
    return { ok: false, status: 0, error: timedOut ? "The API did not answer in time." : "The API is unreachable." };
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // Non-JSON body (e.g. a proxy error page): handled below by status.
  }
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string"
        ? payload.detail
        : `The API answered ${response.status}.`;
    return { ok: false, status: response.status, error: detail };
  }
  if (!validate(payload)) {
    return { ok: false, status: 502, error: "The API returned an unexpected response." };
  }
  return { ok: true, status: response.status, data: payload };
}
