import type { Metadata } from "next";
import Link from "next/link";
import { SearchX, X } from "lucide-react";
import { TopNav } from "@/components/layout/TopNav";
import { PgsLogo } from "@/components/home/PgsLogo";
import { SearchBar } from "@/components/search/SearchBar";
import { SearchTabs } from "@/components/search/SearchTabs";
import { SearchFilters } from "@/components/search/SearchFilters";
import { ResultItem } from "@/components/search/ResultItem";
import { PlaceCard } from "@/components/search/PlaceCard";
import { Pagination } from "@/components/search/Pagination";
import { findPlace } from "@/components/search/places";
import { parseSearchState, searchHref, type SearchState } from "@/components/search/url";
import { searchMock, type PlaceContext } from "@/lib/mock/search";
import { titleCase } from "@/lib/geo";

type SearchPageProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export async function generateMetadata({ searchParams }: SearchPageProps): Promise<Metadata> {
  const { q } = parseSearchState(await searchParams);
  return { title: q ? `${q} — PGS Search` : "Search — PGS Search" };
}

const EXAMPLES = ["Lok Sewa notices", "Kathmandu budget", "Pokhara", "University results", "Kavre"];

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const state = parseSearchState(await searchParams);
  const place = state.q ? await findPlace(state.q) : null;
  const placeContext: PlaceContext | null = place
    ? {
        province: place.province,
        district: place.district,
        municipality: place.kind === "municipality" ? place.name : undefined,
      }
    : null;
  const response = searchMock(state, placeContext);
  const hasFilters = Boolean(state.province || state.district);

  return (
    <div className="flex min-h-screen flex-col bg-white font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <TopNav />

      <header className="border-b border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 pt-2 sm:flex-row sm:items-center sm:gap-6 sm:px-6">
          <Link href="/" aria-label="PGS Search home" className="shrink-0">
            <PgsLogo size="small" />
          </Link>
          <div className="w-full max-w-2xl">
            {/* key: start from the new query when you arrive via a link. */}
            <SearchBar key={state.q} state={state} autoFocus={!state.q} />
          </div>
        </div>
        {state.q && (
          <div className="mx-auto mt-2 flex max-w-6xl flex-col gap-2 px-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <SearchTabs state={state} counts={response.type_counts} />
            <div className="pb-2 sm:pb-0">
              <SearchFilters state={state} />
            </div>
          </div>
        )}
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        {!state.q ? (
          <div className="mx-auto max-w-xl py-12 text-center">
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">What are you looking for?</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              Search news, government notices, universities and organisations across Nepal — or type a place to
              see results from there.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((example) => (
                <Link
                  key={example}
                  href={searchHref(state, { q: example })}
                  className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {example}
                </Link>
              ))}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
            {/* On phones the place card comes first; on wide screens it moves to the side. */}
            {place && (
              <aside className="lg:order-2" aria-label="About this place">
                <div className="lg:sticky lg:top-6">
                  <PlaceCard place={place} state={state} />
                </div>
              </aside>
            )}

            <div className="min-w-0 lg:order-1">
              <h1 className="sr-only">Search results for {state.q}</h1>

              {hasFilters && (
                <div className="mb-4 flex flex-wrap items-center gap-2 text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Showing results from</span>
                  {state.province && (
                    <FilterChip
                      label={`${state.province} Province`}
                      href={searchHref(state, { province: undefined, district: undefined })}
                    />
                  )}
                  {state.district && (
                    <FilterChip label={`${titleCase(state.district)} district`} href={searchHref(state, { district: undefined })} />
                  )}
                  <Link
                    href={searchHref(state, { province: undefined, district: undefined })}
                    className="text-blue-700 hover:underline dark:text-blue-400"
                  >
                    Show all of Nepal
                  </Link>
                </div>
              )}

              <p className="mb-6 text-sm text-slate-500 dark:text-slate-400" role="status">
                {response.total_hits === 0
                  ? "No results"
                  : `${response.total_hits} result${response.total_hits === 1 ? "" : "s"} for “${state.q}”`}
                {response.total_hits > 0 && ` · ${(response.execution_time_ms / 1000).toFixed(2)} seconds`}
                {response.total_pages > 1 && ` · page ${response.page} of ${response.total_pages}`}
                <span className="ml-2 rounded bg-amber-50 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
                  Sample results
                </span>
              </p>

              {response.results.length > 0 ? (
                <>
                  <ol className="space-y-7">
                    {response.results.map((hit) => (
                      <li key={hit.id}>
                        <ResultItem hit={hit} query={state.q} />
                      </li>
                    ))}
                  </ol>
                  <div className="mt-10">
                    <Pagination state={state} page={response.page} totalPages={response.total_pages} />
                  </div>
                </>
              ) : (
                <NoResults state={state} hasFilters={hasFilters} />
              )}

              <RelatedSearches state={state} placeName={place?.name} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function FilterChip({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      aria-label={`Remove filter: ${label}`}
      className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 font-medium text-blue-800 hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20"
    >
      {label}
      <X className="h-3.5 w-3.5" aria-hidden />
    </Link>
  );
}

function NoResults({ state, hasFilters }: { state: SearchState; hasFilters: boolean }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center dark:border-slate-700">
      <SearchX className="mx-auto h-8 w-8 text-slate-400" aria-hidden />
      <p className="mt-3 font-medium text-slate-900 dark:text-slate-100">No results match your search</p>
      <ul className="mt-3 space-y-1 text-sm text-slate-600 dark:text-slate-400">
        {hasFilters && (
          <li>
            Try{" "}
            <Link
              href={searchHref(state, { province: undefined, district: undefined })}
              className="font-medium text-blue-700 hover:underline dark:text-blue-400"
            >
              searching all of Nepal
            </Link>
          </li>
        )}
        {state.type !== "all" && (
          <li>
            Or{" "}
            <Link
              href={searchHref(state, { type: "all" })}
              className="font-medium text-blue-700 hover:underline dark:text-blue-400"
            >
              include all result types
            </Link>
          </li>
        )}
        <li>Check the spelling, or use fewer or more general words.</li>
      </ul>
    </div>
  );
}

function RelatedSearches({ state, placeName }: { state: SearchState; placeName?: string }) {
  const base = state.q.trim();
  const related = Array.from(
    new Set(
      [
        `${base} notice`,
        `${base} news`,
        `${base} report pdf`,
        placeName && !base.toLowerCase().includes(placeName.toLowerCase()) ? `${base} ${placeName}` : null,
        placeName ? `${placeName} municipality office` : null,
      ].filter((s): s is string => Boolean(s) && s!.toLowerCase() !== base.toLowerCase())
    )
  ).slice(0, 5);
  if (related.length === 0) return null;

  return (
    <section aria-labelledby="related-heading" className="mt-12 border-t border-slate-200 pt-6 dark:border-slate-800">
      <h2 id="related-heading" className="text-base font-semibold text-slate-900 dark:text-slate-100">
        Related searches
      </h2>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {related.map((r) => (
          <li key={r}>
            <Link
              href={searchHref(state, { q: r })}
              className="block truncate rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-800 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              {r}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
