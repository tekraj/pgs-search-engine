import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";
import { searchHref, type SearchState } from "@/components/search/url";

// Up to five page numbers around the current one, plus previous / next.
export function Pagination({ state, page, totalPages }: { state: SearchState; page: number; totalPages: number }) {
  if (totalPages <= 1) return null;
  const start = Math.max(1, Math.min(page - 2, totalPages - 4));
  const pages = Array.from({ length: Math.min(5, totalPages) }, (_, i) => start + i);

  const base =
    "inline-flex h-9 min-w-9 items-center justify-center rounded-lg px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";
  const idle =
    "border border-slate-200 text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800";

  return (
    <nav aria-label="Pages of results" className="flex flex-wrap items-center gap-1.5">
      {page > 1 ? (
        <Link href={searchHref(state, { page: page - 1 })} className={cn(base, idle, "gap-1")} rel="prev">
          <ChevronLeft className="h-4 w-4" aria-hidden />
          Previous
        </Link>
      ) : null}
      {pages.map((p) =>
        p === page ? (
          <span key={p} aria-current="page" className={cn(base, "bg-blue-600 text-white")}>
            {p}
          </span>
        ) : (
          <Link key={p} href={searchHref(state, { page: p })} className={cn(base, idle)} aria-label={`Page ${p}`}>
            {p}
          </Link>
        )
      )}
      {page < totalPages ? (
        <Link href={searchHref(state, { page: page + 1 })} className={cn(base, idle, "gap-1")} rel="next">
          Next
          <ChevronRight className="h-4 w-4" aria-hidden />
        </Link>
      ) : null}
    </nav>
  );
}
