import { DISTRICT_TO_PROVINCE, PROVINCE_NAMES } from "@/lib/geo";

// Sample search results, shaped like the documented API response
// (GET /api/v1/user/search in api/README.md: result_type, file_info, geo_tags,
// total_hits, page, total_pages, execution_time_ms) so swapping in the real
// endpoint later only means replacing searchMock().
//
// Results are generated deterministically from the query: the same query
// always gives the same results, so counts, filters and pages stay consistent.

export type ContentType = "all" | "web_page" | "document";
export type SourceKind = "news" | "government" | "education" | "organisation" | "other";

export interface SearchHit {
  id: string;
  result_type: "web_page" | "document";
  title: string;
  url: string;
  domain: string;
  source: SourceKind;
  snippet: string;
  published_date: string;
  file_info?: { extension: string; formatted_size: string; download_url: string };
  geo_tags?: { province: string; district: string; municipality?: string };
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  page: number;
  total_pages: number;
  execution_time_ms: number;
  results: SearchHit[];
  // Totals per tab, so the tabs can show counts without extra requests.
  type_counts: Record<ContentType, number>;
}

/** The place a query is about, if any — makes most sample results tagged to it. */
export interface PlaceContext {
  province: string;
  district?: string;
  municipality?: string;
}

export interface SearchParams {
  q: string;
  type: ContentType;
  province?: string;
  district?: string;
  page: number;
}

export const PAGE_SIZE = 10;

export const SOURCE_LABELS: Record<SourceKind, string> = {
  news: "News",
  government: "Government",
  education: "Education",
  organisation: "Organisation",
  other: "Website",
};

const SOURCE_DOMAINS: Record<SourceKind, string[]> = {
  news: ["news.pgs.np", "khabar.pgs.np"],
  government: ["gov.pgs.np", "notice.pgs.np"],
  education: ["edu.pgs.np"],
  organisation: ["biz.pgs.np"],
  other: ["web.pgs.np"],
};

const SOURCES: SourceKind[] = ["news", "news", "government", "government", "education", "organisation", "other"];

type Template = (q: string, place: string) => { title: string; snippet: string };

const WEB_TEMPLATES: Record<SourceKind, Template[]> = {
  news: [
    (q, p) => ({
      title: `${q}: what changes for residents of ${p}`,
      snippet: `Local officials in ${p} explained how ${q} affects services, budgets and ward offices over the coming months.`,
    }),
    (q, p) => ({
      title: `${p} update — ${q}`,
      snippet: `The latest on ${q} in ${p}, including reactions from community members and the next steps announced this week.`,
    }),
  ],
  government: [
    (q, p) => ({
      title: `Public notice regarding ${q} — ${p}`,
      snippet: `Official notice issued for ${p} about ${q}. Includes eligibility, deadlines and the office to contact for details.`,
    }),
    (q, p) => ({
      title: `${q}: guidelines and procedures (${p})`,
      snippet: `Procedures, required documents and fees related to ${q}, published for residents and businesses in ${p}.`,
    }),
  ],
  education: [
    (q, p) => ({
      title: `${q} — information for students in ${p}`,
      snippet: `Admission dates, results and course information related to ${q} for colleges and schools in ${p}.`,
    }),
  ],
  organisation: [
    (q, p) => ({
      title: `${q} services in ${p}`,
      snippet: `Branch details, rates and service updates related to ${q} for customers in ${p}.`,
    }),
  ],
  other: [
    (q, p) => ({
      title: `${q} — a guide for ${p}`,
      snippet: `A community-maintained overview of ${q} in ${p}, with links to official sources and contact information.`,
    }),
  ],
};

const DOCUMENT_TEMPLATES: Template[] = [
  (q, p) => ({ title: `${q} — annual report, ${p}`, snippet: `Annual report covering ${q} in ${p}: figures, progress and plans for the next fiscal year.` }),
  (q, p) => ({ title: `${q}: official circular (${p})`, snippet: `Circular on ${q} issued for offices in ${p}, with effective dates and responsibilities.` }),
  (q, p) => ({ title: `${q} budget allocation — ${p}`, snippet: `Budget tables for ${q} in ${p}, broken down by ward and programme.` }),
];

const DISTRICTS = Object.keys(DISTRICT_TO_PROVINCE);

function seededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 9301 + 49297) % 233280;
    return value / 233280;
  };
}

function hashString(input: string): number {
  let hash = 0;
  for (let i = 0; i < input.length; i++) {
    hash = (hash << 5) - hash + input.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash) || 1;
}

function titleCaseDistrict(district: string): string {
  return district
    .toLowerCase()
    .split(" ")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || "result";
}

// The full, unfiltered result set for a query. Independent of filters, so
// totals and tab counts never contradict each other.
function generatePool(query: string, place: PlaceContext | null): SearchHit[] {
  const rand = seededRandom(hashString(query.toLowerCase()));
  const pick = <T,>(items: T[]) => items[Math.floor(rand() * items.length)];
  const size = 18 + (hashString(query) % 23);
  const placeDistricts = place
    ? place.district
      ? [place.district]
      : DISTRICTS.filter((d) => DISTRICT_TO_PROVINCE[d] === place.province)
    : DISTRICTS;
  const now = Date.now();

  // Titles read as sentences ("Pokhara budget…", not "pokhara budget…").
  const displayQuery = query.charAt(0).toUpperCase() + query.slice(1);
  const usedTitles = new Set<string>();

  const hits: SearchHit[] = [];
  for (let i = 0; i < size; i++) {
    // Most results about the queried place are tagged to it; the rest spread
    // across the country, like a real index would.
    const aboutPlace = place !== null && rand() < 0.75;
    const district = aboutPlace ? pick(placeDistricts) : pick(DISTRICTS);
    const municipality = aboutPlace && place?.municipality ? place.municipality : undefined;
    const placeName = municipality ?? titleCaseDistrict(district);

    const isDocument = rand() < 0.28;
    const source = isDocument ? pick<SourceKind>(["government", "government", "education", "organisation"]) : pick(SOURCES);
    const template = isDocument ? pick(DOCUMENT_TEMPLATES) : pick(WEB_TEMPLATES[source]);
    const generated = template(displayQuery, placeName);
    const { snippet } = template(query, placeName);
    // Real indexes rarely return two identical titles; number repeats like
    // multi-part notices instead.
    let title = generated.title;
    for (let n = 2; usedTitles.has(title); n++) title = `${generated.title} (part ${n})`;
    usedTitles.add(title);
    const domain = pick(SOURCE_DOMAINS[source]);
    const path = `${slugify(placeName)}/${slugify(query)}-${1000 + Math.floor(rand() * 8999)}`;
    const daysAgo = Math.floor(rand() * rand() * 400);

    hits.push({
      id: `${slugify(query)}-${i}`,
      result_type: isDocument ? "document" : "web_page",
      title,
      url: `https://${domain}/${path}${isDocument ? ".pdf" : ""}`,
      domain,
      source,
      snippet,
      published_date: new Date(now - daysAgo * 86_400_000).toISOString(),
      file_info: isDocument
        ? {
            extension: "pdf",
            formatted_size: `${(0.2 + rand() * 4.8).toFixed(1)} MB`,
            download_url: `https://${domain}/${path}.pdf`,
          }
        : undefined,
      geo_tags: { province: DISTRICT_TO_PROVINCE[district], district, municipality },
    });
  }

  // Relevance: results about the queried place first, generation order otherwise.
  if (place) {
    const matches = (h: SearchHit) =>
      place.district ? h.geo_tags?.district === place.district : h.geo_tags?.province === place.province;
    hits.sort((a, b) => Number(matches(b)) - Number(matches(a)));
  }
  return hits;
}

/** Stand-in for GET /api/v1/user/search. */
export function searchMock(params: SearchParams, place: PlaceContext | null): SearchResponse {
  const query = params.q.trim();
  const empty: SearchResponse = {
    query,
    total_hits: 0,
    page: 1,
    total_pages: 0,
    execution_time_ms: 0,
    results: [],
    type_counts: { all: 0, web_page: 0, document: 0 },
  };
  if (!query) return empty;

  const provinceName = params.province
    ? Object.values(PROVINCE_NAMES).find((p) => p.replace(" Province", "").toLowerCase() === params.province!.toLowerCase())
    : undefined;
  const district = params.district?.toUpperCase();

  const located = generatePool(query, place).filter(
    (h) =>
      (!provinceName || h.geo_tags?.province === provinceName) && (!district || h.geo_tags?.district === district)
  );
  const type_counts: Record<ContentType, number> = {
    all: located.length,
    web_page: located.filter((h) => h.result_type === "web_page").length,
    document: located.filter((h) => h.result_type === "document").length,
  };
  const filtered = params.type === "all" ? located : located.filter((h) => h.result_type === params.type);

  const total_pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, params.page), total_pages);

  return {
    query,
    total_hits: filtered.length,
    page,
    total_pages,
    execution_time_ms: 12 + (hashString(query) % 45),
    results: filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE),
    type_counts,
  };
}
