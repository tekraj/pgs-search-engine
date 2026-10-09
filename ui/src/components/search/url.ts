import type { ContentType } from "@/lib/mock/search";

export interface SearchState {
  q: string;
  type: ContentType;
  province?: string;
  district?: string;
  page: number;
}

/**
 * Builds a /search URL from the current state plus changes. Changing anything
 * other than the page sends you back to page 1, so you never land on a page
 * that no longer exists.
 */
export function searchHref(state: SearchState, changes: Partial<SearchState> = {}): string {
  const next = { ...state, ...changes };
  if (!("page" in changes)) next.page = 1;

  const params = new URLSearchParams();
  if (next.q) params.set("q", next.q);
  if (next.type !== "all") params.set("type", next.type);
  if (next.province) params.set("province", next.province);
  if (next.district) params.set("district", next.district);
  if (next.page > 1) params.set("page", String(next.page));
  const query = params.toString();
  return query ? `/search?${query}` : "/search";
}

export function parseSearchState(raw: Record<string, string | string[] | undefined>): SearchState {
  const get = (key: string) => {
    const value = raw[key];
    return (Array.isArray(value) ? value[0] : value)?.trim() || undefined;
  };
  const type = get("type");
  const page = Number.parseInt(get("page") ?? "1", 10);
  return {
    q: get("q") ?? "",
    type: type === "web_page" || type === "document" ? type : "all",
    province: get("province"),
    district: get("district"),
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}
