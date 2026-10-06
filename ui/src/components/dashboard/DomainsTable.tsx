"use client";

import { useMemo, useState } from "react";
import { Lock, Pause, Play, RotateCw, Search, X } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { formatFullDate, formatNumber, percent, timeAgo } from "@/components/dashboard/format";
import type { DomainRow, DomainStatus } from "@/lib/mock/metrics";

const STATUS: Record<DomainStatus, { label: string; className: string }> = {
  CRAWLING: { label: "Crawling", className: "bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300" },
  PENDING: { label: "Waiting", className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300" },
  COMPLETED: { label: "Done", className: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300" },
  FAILED: { label: "Failed", className: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300" },
  PAUSED: { label: "Paused", className: "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300" },
};

const FILTERS: Array<DomainStatus | "ALL"> = ["ALL", "CRAWLING", "PENDING", "COMPLETED", "FAILED", "PAUSED"];

type Action = "PAUSE" | "RESUME" | "RE_CRAWL";

/** Which action makes sense for a website in this state (POST /admin/domains/{domain}/action). */
function actionFor(status: DomainStatus): { action: Action; label: string; icon: typeof Pause } {
  if (status === "CRAWLING" || status === "PENDING") return { action: "PAUSE", label: "Pause", icon: Pause };
  if (status === "PAUSED") return { action: "RESUME", label: "Resume", icon: Play };
  return { action: "RE_CRAWL", label: "Crawl again", icon: RotateCw };
}

const NEXT_STATUS: Record<Action, DomainStatus> = { PAUSE: "PAUSED", RESUME: "PENDING", RE_CRAWL: "PENDING" };
const DONE_MESSAGE: Record<Action, string> = {
  PAUSE: "paused",
  RESUME: "resumed — it will be crawled next",
  RE_CRAWL: "queued to be crawled again",
};

export function DomainsTable({
  domains,
  totalRegistered,
  now,
  canManage,
}: {
  domains: DomainRow[];
  totalRegistered: number;
  now: number;
  canManage: boolean;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<DomainStatus | "ALL">("ALL");
  // Status changes made in this session (sample data: nothing is sent yet).
  const [overrides, setOverrides] = useState<Record<string, DomainStatus>>({});
  const [notice, setNotice] = useState("");

  const rows = useMemo(
    () => domains.map((d) => (overrides[d.domain] ? { ...d, status: overrides[d.domain] } : d)),
    [domains, overrides]
  );

  const counts = useMemo(() => {
    const c: Record<DomainStatus | "ALL", number> = { ALL: rows.length, CRAWLING: 0, PENDING: 0, COMPLETED: 0, FAILED: 0, PAUSED: 0 };
    for (const r of rows) c[r.status] += 1;
    return c;
  }, [rows]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter(
      (r) =>
        (filter === "ALL" || r.status === filter) &&
        (!q || r.domain.includes(q) || r.category.toLowerCase().includes(q))
    );
  }, [rows, filter, query]);

  function runAction(row: DomainRow, action: Action) {
    setOverrides((prev) => ({ ...prev, [row.domain]: NEXT_STATUS[action] }));
    setNotice(`${row.domain} ${DONE_MESSAGE[action]}. (Sample data: not sent to the server yet.)`);
  }

  return (
    <Card>
      <div className="flex flex-col gap-3 border-b border-slate-200 p-4 dark:border-slate-800">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Showing {visible.length} of {rows.length} sample websites
            <span className="text-slate-400"> · {formatNumber(totalRegistered)} registered in total</span>
          </p>
          <label className="relative block sm:w-64">
            <span className="sr-only">Search websites</span>
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search websites…"
              className="w-full rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </label>
        </div>

        <div role="group" aria-label="Filter by status" className="flex gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              aria-pressed={filter === f}
              className={cn(
                "flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                filter === f
                  ? "bg-slate-900 font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              )}
            >
              {f === "ALL" ? "All" : STATUS[f].label}
              <span className={cn("text-xs tabular-nums", filter === f ? "opacity-80" : "text-slate-400")}>{counts[f]}</span>
            </button>
          ))}
        </div>

        {!canManage && (
          <p className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <Lock className="h-3.5 w-3.5" aria-hidden />
            You can view websites. Only administrators can pause or re-crawl them.
          </p>
        )}
      </div>

      <p role="status" className={cn("text-sm", notice && "flex items-start justify-between gap-3 border-b border-slate-200 bg-blue-50 px-4 py-2 text-blue-900 dark:border-slate-800 dark:bg-blue-500/10 dark:text-blue-200")}>
        {notice && (
          <>
            <span>{notice}</span>
            <button
              type="button"
              onClick={() => setNotice("")}
              aria-label="Dismiss message"
              className="shrink-0 rounded p-0.5 hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-blue-500/20"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </>
        )}
      </p>

      {visible.length === 0 ? (
        <div className="px-4 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
          No websites match.{" "}
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setFilter("ALL");
            }}
            className="font-medium text-blue-700 hover:underline dark:text-blue-400"
          >
            Clear search and filters
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="text-xs text-slate-500 dark:text-slate-400">
              <tr className="border-b border-slate-200 dark:border-slate-800">
                <th scope="col" className="px-4 py-2 font-medium">Website</th>
                <th scope="col" className="px-4 py-2 font-medium">Status</th>
                <th scope="col" className="px-4 py-2 font-medium">Pages crawled</th>
                <th scope="col" className="px-4 py-2 font-medium">Failed</th>
                <th scope="col" className="px-4 py-2 font-medium">Last crawled</th>
                <th scope="col" className="px-4 py-2 text-right font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {visible.map((row) => {
                const done = percent(row.scraped_pages, row.discovered_child_links);
                const failRate = percent(row.failed_pages, row.discovered_child_links);
                const { action, label, icon: Icon } = actionFor(row.status);
                return (
                  <tr key={row.domain} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                    <th scope="row" className="px-4 py-3 font-normal">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{row.domain}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {row.category} · {row.rate_limit_per_sec} req/sec
                      </p>
                    </th>
                    <td className="px-4 py-3">
                      <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium", STATUS[row.status].className)}>
                        {STATUS[row.status].label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {row.discovered_child_links > 0 ? (
                        <div className="w-36">
                          <p className="text-xs tabular-nums text-slate-700 dark:text-slate-300">
                            {formatNumber(row.scraped_pages)} <span className="text-slate-400">of {formatNumber(row.discovered_child_links)}</span>
                          </p>
                          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-hidden>
                            <div className="h-full rounded-full bg-blue-500" style={{ width: `${done}%` }} />
                          </div>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-400">Not started</span>
                      )}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      <span
                        className={cn(
                          "text-xs",
                          failRate >= 10 ? "font-medium text-rose-700 dark:text-rose-400" : "text-slate-600 dark:text-slate-400"
                        )}
                      >
                        {formatNumber(row.failed_pages)}
                        {failRate >= 10 && ` (${failRate}%)`}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                      {row.last_crawled_at ? (
                        <time dateTime={row.last_crawled_at} title={formatFullDate(row.last_crawled_at)}>
                          {timeAgo(row.last_crawled_at, now)}
                        </time>
                      ) : (
                        "Never"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        disabled={!canManage}
                        onClick={() => runAction(row, action)}
                        title={canManage ? undefined : "Only administrators can do this"}
                        aria-label={`${label}: ${row.domain}`}
                        className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                      >
                        <Icon className="h-3.5 w-3.5" aria-hidden />
                        {label}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
