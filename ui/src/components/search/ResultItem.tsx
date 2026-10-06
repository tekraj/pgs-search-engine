import Link from "next/link";
import { Download, FileText, MapPin } from "lucide-react";
import { cn } from "@/lib/cn";
import { getProvinceColor, titleCase } from "@/lib/geo";
import { SOURCE_LABELS, type SearchHit, type SourceKind } from "@/lib/mock/search";

const SOURCE_STYLES: Record<SourceKind, string> = {
  news: "bg-sky-50 text-sky-800 dark:bg-sky-500/10 dark:text-sky-300",
  government: "bg-emerald-50 text-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300",
  education: "bg-violet-50 text-violet-800 dark:bg-violet-500/10 dark:text-violet-300",
  organisation: "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300",
  other: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
};

const DATE_FORMAT = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });

function formatDate(iso: string): string {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return DATE_FORMAT.format(new Date(iso));
}

// Bold the words the user searched for. Done with plain text splitting (not
// injected HTML), so result text can never inject markup.
function Highlighted({ text, query }: { text: string; query: string }) {
  const terms = query
    .toLowerCase()
    .split(/\s+/)
    .filter((t) => t.length >= 2)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (terms.length === 0) return <>{text}</>;
  const parts = text.split(new RegExp(`(${terms.join("|")})`, "gi"));
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-slate-900 dark:text-slate-100">
            {part}
          </strong>
        ) : (
          part
        )
      )}
    </>
  );
}

export function ResultItem({ hit, query }: { hit: SearchHit; query: string }) {
  const url = new URL(hit.url);
  const crumbs = url.pathname.split("/").filter(Boolean).slice(0, -1);
  const geo = hit.geo_tags;
  const placeLabel = geo ? (geo.municipality ?? titleCase(geo.district)) : null;
  const placeHref = geo
    ? geo.municipality
      ? `/map?focus=${encodeURIComponent(geo.municipality)}&district=${encodeURIComponent(titleCase(geo.district))}`
      : `/map?focus=${encodeURIComponent(titleCase(geo.district))}`
    : null;

  return (
    <article className="group">
      <div className="flex items-center gap-2.5">
        <span
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-white text-xs font-semibold uppercase text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
          aria-hidden
        >
          {hit.domain[0]}
        </span>
        <div className="min-w-0 text-sm leading-tight">
          <p className="truncate text-slate-800 dark:text-slate-200">{hit.domain}</p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {[url.hostname, ...crumbs].join(" › ")}
          </p>
        </div>
      </div>

      <h3 className="mt-1.5 text-lg leading-snug">
        <a
          href={hit.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-700 underline-offset-2 visited:text-violet-700 hover:underline focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-blue-400 dark:visited:text-violet-400"
        >
          {hit.result_type === "document" && (
            <span className="mr-1.5 inline-flex -translate-y-0.5 items-center rounded bg-rose-100 px-1.5 py-0.5 align-middle text-[11px] font-bold uppercase text-rose-700 dark:bg-rose-500/15 dark:text-rose-300">
              {hit.file_info?.extension ?? "doc"}
            </span>
          )}
          {hit.title}
        </a>
      </h3>

      <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        <span className="text-slate-500 dark:text-slate-500">{formatDate(hit.published_date)} — </span>
        <Highlighted text={hit.snippet} query={query} />
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
        <span className={cn("rounded-full px-2 py-0.5 font-medium", SOURCE_STYLES[hit.source])}>
          {SOURCE_LABELS[hit.source]}
        </span>
        {placeLabel && placeHref && geo && (
          <Link
            href={placeHref}
            className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 text-slate-700 hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            title="Show this place on the map"
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{ backgroundColor: getProvinceColor(geo.province) }}
              aria-hidden
            />
            <MapPin className="h-3 w-3" aria-hidden />
            {placeLabel}
          </Link>
        )}
        {hit.file_info && (
          <>
            <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400">
              <FileText className="h-3 w-3" aria-hidden />
              {hit.file_info.formatted_size}
            </span>
            <a
              href={hit.file_info.download_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 px-2 py-0.5 font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              <Download className="h-3 w-3" aria-hidden />
              Download
            </a>
          </>
        )}
      </div>
    </article>
  );
}
