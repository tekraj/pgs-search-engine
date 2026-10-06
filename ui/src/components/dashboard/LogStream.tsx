"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { formatClock, formatFullDate } from "@/components/dashboard/format";
import { generateLiveLog, type LogSeverity, type SystemLog } from "@/lib/mock/metrics";

const SEVERITY: Record<LogSeverity, string> = {
  INFO: "text-sky-300",
  WARN: "text-amber-300",
  ERROR: "text-rose-300",
  FATAL: "bg-rose-500/20 text-rose-200",
};

const FILTERS: { key: string; label: string; levels: LogSeverity[] }[] = [
  { key: "all", label: "Everything", levels: ["INFO", "WARN", "ERROR", "FATAL"] },
  { key: "problems", label: "Warnings & errors", levels: ["WARN", "ERROR", "FATAL"] },
  { key: "errors", label: "Errors only", levels: ["ERROR", "FATAL"] },
];

const MAX_LINES = 200;
const UPDATE_MS = 2500;

export function LogStream({ initialLogs }: { initialLogs: SystemLog[] }) {
  const [logs, setLogs] = useState(initialLogs);
  const [live, setLive] = useState(true);
  const [filterKey, setFilterKey] = useState("all");
  const scrollRef = useRef<HTMLDivElement>(null);
  // Only follow new lines while the reader is at the bottom, so scrolling up
  // to read an older line doesn't get yanked away.
  const pinnedRef = useRef(true);

  useEffect(() => {
    if (!live) return;
    const interval = setInterval(() => {
      if (document.hidden) return;
      setLogs((prev) => [...prev.slice(-(MAX_LINES - 1)), generateLiveLog()]);
    }, UPDATE_MS);
    return () => clearInterval(interval);
  }, [live]);

  const filter = FILTERS.find((f) => f.key === filterKey) ?? FILTERS[0];
  const visible = useMemo(() => logs.filter((l) => filter.levels.includes(l.severity)), [logs, filter]);
  const problemCount = logs.filter((l) => l.severity === "ERROR" || l.severity === "FATAL").length;

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && pinnedRef.current) el.scrollTop = el.scrollHeight;
  }, [visible]);

  function onScroll() {
    const el = scrollRef.current;
    if (el) pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  }

  return (
    <Card>
      <CardHeader
        title="System logs"
        subtitle={`${logs.length} recent lines · ${problemCount} errors · times in Nepal time (NPT)`}
        action={
          <button
            type="button"
            onClick={() => setLive((v) => !v)}
            aria-pressed={!live}
            className="flex shrink-0 items-center gap-1.5 rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {live ? (
              <>
                <span className="relative flex h-2 w-2" aria-hidden>
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:animate-none" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                Live
                <Pause className="h-3 w-3" aria-hidden />
              </>
            ) : (
              <>
                <Play className="h-3 w-3" aria-hidden />
                Paused — resume
              </>
            )}
          </button>
        }
      />

      <div role="group" aria-label="Show" className="flex gap-1 overflow-x-auto border-b border-slate-200 px-4 py-2 [scrollbar-width:none] dark:border-slate-800 [&::-webkit-scrollbar]:hidden">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFilterKey(f.key)}
            aria-pressed={filterKey === f.key}
            className={cn(
              "shrink-0 rounded-full px-3 py-1 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
              filterKey === f.key
                ? "bg-slate-900 font-medium text-white dark:bg-slate-100 dark:text-slate-900"
                : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div
        ref={scrollRef}
        onScroll={onScroll}
        tabIndex={0}
        aria-label="Log lines"
        className="h-80 overflow-y-auto rounded-b-xl bg-slate-950 p-3 font-mono text-xs leading-relaxed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500"
      >
        {visible.length === 0 ? (
          <p className="text-slate-500">Nothing at this level yet.</p>
        ) : (
          <ol className="space-y-1">
            {visible.map((log) => (
              <li key={log.log_id} className="grid grid-cols-[auto_auto_1fr] gap-x-2 sm:grid-cols-[auto_auto_minmax(0,11rem)_1fr]">
                <time dateTime={log.timestamp} title={formatFullDate(log.timestamp)} className="text-slate-500">
                  {formatClock(log.timestamp, true)}
                </time>
                <span className={cn("w-12 rounded px-1 text-center font-semibold", SEVERITY[log.severity])}>{log.severity}</span>
                <span className="hidden truncate text-slate-400 sm:block" title={log.service}>
                  {log.service}
                </span>
                <span className="col-span-3 break-words text-slate-200 sm:col-span-1">
                  <span className="text-slate-400 sm:hidden">{log.service}: </span>
                  {log.message}
                  {log.domain && <span className="text-slate-500"> · {log.domain}</span>}
                </span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </Card>
  );
}
