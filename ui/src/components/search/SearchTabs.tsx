import Link from "next/link";
import { cn } from "@/lib/cn";
import type { ContentType } from "@/lib/mock/search";
import { searchHref, type SearchState } from "@/components/search/url";

// The content types the search API filters on (content_type: all | web_page |
// document). Plain links, so each tab has its own shareable URL.
const TABS: { type: ContentType; label: string }[] = [
  { type: "all", label: "All" },
  { type: "web_page", label: "Web pages" },
  { type: "document", label: "Documents" },
];

export function SearchTabs({ state, counts }: { state: SearchState; counts: Record<ContentType, number> }) {
  return (
    <nav
      aria-label="Result type"
      className="flex gap-1 overflow-x-auto overflow-y-hidden [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {TABS.map((tab) => {
        const active = state.type === tab.type;
        return (
          <Link
            key={tab.type}
            href={searchHref(state, { type: tab.type })}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500",
              active
                ? "border-blue-600 text-blue-700 dark:border-blue-400 dark:text-blue-400"
                : "border-transparent text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            )}
          >
            {tab.label}
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs",
                active
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-500/15 dark:text-blue-300"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              )}
            >
              {counts[tab.type]}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
