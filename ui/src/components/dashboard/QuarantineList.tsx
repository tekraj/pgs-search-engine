import { FileWarning, ShieldCheck } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { formatFullDate, formatNumber, timeAgo } from "@/components/dashboard/format";
import type { QuarantinedFile, StorageMetrics } from "@/lib/mock/metrics";

function formatSize(kb: number) {
  return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
}

export function QuarantineList({
  files,
  store,
  now,
}: {
  files: QuarantinedFile[];
  store: StorageMetrics["quarantine_store"];
  now: number;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
          <ShieldCheck className="h-4 w-4" aria-hidden />
          Protection is on
        </div>
        <p className="mt-3 text-3xl font-semibold tabular-nums tracking-tight text-slate-900 dark:text-slate-50">
          {formatNumber(store.count)}
        </p>
        <p className="text-sm text-slate-600 dark:text-slate-400">unsafe files blocked ({store.size_mb} MB)</p>
        <p className="mt-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
          ClamAV scans every downloaded file. Infected files are moved to quarantine and never reach search
          results.
        </p>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Latest threat: <span className="font-mono text-slate-700 dark:text-slate-300">{store.latest_threat_detected}</span>
        </p>
      </div>

      <Card>
        <CardHeader title="Recently quarantined" subtitle="Newest first" />
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {files.map((file) => (
            <li key={file.file_id} className="flex items-start gap-3 px-4 py-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400">
                <FileWarning className="h-4 w-4" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className="truncate font-mono text-sm font-medium text-slate-900 dark:text-slate-100">{file.file_name}</p>
                  <time dateTime={file.detected_at} title={formatFullDate(file.detected_at)} className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                    {timeAgo(file.detected_at, now)}
                  </time>
                </div>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                  from {file.domain} · {formatSize(file.size_kb)}
                </p>
                <p className="mt-1 inline-flex rounded bg-rose-50 px-1.5 py-0.5 font-mono text-[11px] text-rose-700 dark:bg-rose-500/10 dark:text-rose-300">
                  {file.threat}
                </p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
