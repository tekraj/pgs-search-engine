import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Info, SearchX, TriangleAlert } from "lucide-react";
import { TopNav } from "@/components/layout/TopNav";
import { SearchBox } from "@/components/home/SearchBox";
import { SearchTabs } from "@/components/search/SearchTabs";
import { ResultItem } from "@/components/search/ResultItem";
import { PgsLogo } from "@/components/home/PgsLogo";
import { apiFetch } from "@/lib/api/server";
import { MAX_QUERY_LENGTH, MAX_RESULT_WINDOW, isSearchResponse } from "@/lib/api/types";

const PAGE_SIZE = 10;

function firstValue(value: string | string[] | undefined): string {
  return (Array.isArray(value) ? value[0] : value) ?? "";
}

type SearchPageProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };

// The browser tab shows what was searched for, e.g. "Kathmandu budget — PGS Search".
export async function generateMetadata({ searchParams }: SearchPageProps): Promise<Metadata> {
  const q = firstValue((await searchParams).q).trim().slice(0, 80);
  return { title: q ? `${q} — PGS Search` : "Search — PGS Search" };
}

export default async function SearchPage({ searchParams }: SearchPageProps) {
  const params = await searchParams;
  const q = firstValue(params.q).trim().slice(0, MAX_QUERY_LENGTH);
  const requestedPage = Number.parseInt(firstValue(params.page), 10);
  const maxPage = Math.floor(MAX_RESULT_WINDOW / PAGE_SIZE);
  const page = Number.isFinite(requestedPage) ? Math.min(Math.max(requestedPage, 1), maxPage) : 1;

  const result = q
    ? await apiFetch("/api/v1/search", isSearchResponse, {
        searchParams: { q, page, limit: PAGE_SIZE },
      })
    : null;

  const pageHref = (target: number) => `/search?${new URLSearchParams({ q, page: String(target) })}`;

  return (
    <div className="flex min-h-screen flex-col bg-white font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <TopNav />

      <header className="border-b border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 pt-2 sm:flex-row sm:items-center sm:gap-6 sm:px-6">
          <Link
            href="/"
            aria-label="PGS Search home"
            className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <PgsLogo size="small" />
          </Link>
          <div className="w-full max-w-2xl">
            <SearchBox autoFocus={false} initialValue={q} compact />
          </div>
        </div>
        <div className="mx-auto mt-2 max-w-6xl px-4 sm:px-6">
          <SearchTabs />
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        {!q ? (
          <div className="mx-auto max-w-xl py-16 text-center">
            <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">What are you looking for?</h1>
            <p className="mt-2 text-slate-600 dark:text-slate-400">Type a query above to search.</p>
          </div>
        ) : !result?.ok ? (
          <div
            role="alert"
            className="flex max-w-2xl items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-900 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100"
          >
            <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" aria-hidden />
            <div>
              <p className="font-medium">Search is unavailable right now</p>
              <p className="mt-0.5 text-sm opacity-80">{result?.error}</p>
            </div>
          </div>
        ) : (
          <>
            <h1 className="sr-only">Search results for {q}</h1>
            <div className="mb-6 flex max-w-2xl flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
              <p role="status">
                {result.data.total_hits === 0 ? (
                  <>No results for &ldquo;{q}&rdquo;.</>
                ) : (
                  <>
                    {result.data.total_hits.toLocaleString("en-US")} result{result.data.total_hits === 1 ? "" : "s"} for{" "}
                    &ldquo;<span className="font-medium text-slate-700 dark:text-slate-300">{q}</span>&rdquo; ({result.data.took_ms} ms)
                  </>
                )}
              </p>
              {result.data.degraded ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
                  <Info className="h-3 w-3" aria-hidden />
                  some ranking signals were unavailable
                </span>
              ) : null}
            </div>

            {result.data.total_hits === 0 ? (
              <div className="max-w-2xl rounded-2xl border border-dashed border-slate-300 px-6 py-10 text-center dark:border-slate-700">
                <SearchX className="mx-auto h-8 w-8 text-slate-400" aria-hidden />
                <p className="mt-3 font-medium text-slate-900 dark:text-slate-100">No pages match &ldquo;{q}&rdquo;</p>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Check the spelling, or try fewer or more general words.
                </p>
              </div>
            ) : (
              <ol className="space-y-8">
                {result.data.results.map((item) => (
                  <li key={item.id}>
                    <ResultItem result={item} />
                  </li>
                ))}
              </ol>
            )}

            <nav className="mt-10 flex max-w-2xl items-center gap-3 text-sm" aria-label="Result pages">
              {page > 1 ? (
                <Link
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 font-medium text-blue-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-blue-400 dark:hover:bg-slate-800"
                  href={pageHref(page - 1)}
                >
                  <ArrowLeft className="h-4 w-4" aria-hidden />
                  Previous
                </Link>
              ) : null}
              {page > 1 || page * PAGE_SIZE < Math.min(result.data.total_hits, MAX_RESULT_WINDOW) ? (
                <span className="text-slate-500 dark:text-slate-400">Page {page}</span>
              ) : null}
              {page * PAGE_SIZE < Math.min(result.data.total_hits, MAX_RESULT_WINDOW) ? (
                <Link
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 font-medium text-blue-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-blue-400 dark:hover:bg-slate-800"
                  href={pageHref(page + 1)}
                >
                  Next
                  <ArrowRight className="h-4 w-4" aria-hidden />
                </Link>
              ) : null}
            </nav>
          </>
        )}
      </main>
    </div>
  );
}
