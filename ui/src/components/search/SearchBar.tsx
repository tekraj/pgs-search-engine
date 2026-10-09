"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Search, X } from "lucide-react";
import { searchHref, type SearchState } from "@/components/search/url";

// The search page's own search box: a new query keeps the current tab and
// location filters and starts again from page 1.
export function SearchBar({ state, autoFocus = false }: { state: SearchState; autoFocus?: boolean }) {
  const router = useRouter();
  const [value, setValue] = useState(state.q);

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim();
        if (q) router.push(searchHref(state, { q }));
      }}
      className="flex w-full items-center gap-2 rounded-xl border border-slate-300 bg-white p-1 pl-3.5 shadow-sm transition-shadow focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-500/15 dark:border-slate-700 dark:bg-slate-900"
    >
      <label htmlFor="search-page-input" className="sr-only">
        Search
      </label>
      <Search className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
      <input
        id="search-page-input"
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoFocus={autoFocus}
        autoComplete="off"
        placeholder="Search news, notices, offices, or a place"
        className="h-9 min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100 [&::-webkit-search-cancel-button]:hidden"
      />
      {value && (
        <button
          type="button"
          onClick={() => setValue("")}
          aria-label="Clear search"
          className="rounded p-1 text-slate-400 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:text-slate-200"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      <button
        type="submit"
        className="h-9 shrink-0 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900"
      >
        Search
      </button>
    </form>
  );
}
