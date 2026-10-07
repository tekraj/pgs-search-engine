import { CalendarDays, MapPin } from "lucide-react";
import type { SearchResult } from "@/lib/api/types";

function placeLabel(result: SearchResult): string | null {
  const geo = result.geo;
  if (!geo) return null;
  return [geo.municipality_name, geo.district_name, geo.province_name].filter(Boolean).join(", ") || null;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "16 Sep 2026" (UTC, so the server and the browser print the same text). */
function formatDate(date: Date): string {
  return `${date.getUTCDate()} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()}`;
}

/** "https://psc.gov.np/notice/123" → "psc.gov.np › notice › 123" */
function breadcrumb(url: string): string {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    return [u.hostname.replace(/^www\./, ""), ...parts].join(" › ");
  } catch {
    return url;
  }
}

export function ResultItem({ result }: { result: SearchResult }) {
  const place = placeLabel(result);
  const published = result.published_at ? new Date(result.published_at) : null;
  const hasDate = published && !Number.isNaN(published.getTime());

  return (
    <article className="group max-w-2xl">
      <div className="flex items-center gap-2.5">
        <span
          aria-hidden
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300"
        >
          {result.domain.replace(/^www\./, "").charAt(0)}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm text-slate-800 dark:text-slate-200">{result.domain}</p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400" title={result.url}>
            {breadcrumb(result.url)}
          </p>
        </div>
      </div>

      <h2 className="mt-1.5">
        <a
          href={result.url}
          rel="noopener noreferrer nofollow"
          target="_blank"
          className="text-lg leading-snug text-blue-700 underline-offset-2 hover:underline focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 visited:text-violet-700 dark:text-blue-400 dark:visited:text-violet-400"
        >
          {result.title || result.url}
        </a>
      </h2>

      {result.snippet && (
        <p className="mt-1 line-clamp-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{result.snippet}</p>
      )}

      {(place || hasDate) && (
        <p className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
          {place ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300">
              <MapPin className="h-3 w-3" aria-hidden />
              {place}
            </span>
          ) : null}
          {hasDate ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 dark:bg-slate-800">
              <CalendarDays className="h-3 w-3" aria-hidden />
              <time dateTime={published!.toISOString()}>{formatDate(published!)}</time>
            </span>
          ) : null}
        </p>
      )}
    </article>
  );
}
