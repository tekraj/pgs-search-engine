import { cn } from "@/lib/cn";
import type { ServiceHealth as Service, ServiceState } from "@/lib/mock/metrics";

const STATE: Record<ServiceState, { label: string; dot: string; pill: string }> = {
  UP: {
    label: "Running",
    dot: "bg-emerald-500",
    pill: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300",
  },
  DEGRADED: {
    label: "Needs attention",
    dot: "bg-amber-500",
    pill: "bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-300",
  },
  DOWN: {
    label: "Down",
    dot: "bg-rose-500",
    pill: "bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300",
  },
};

export function ServiceHealth({ services }: { services: Service[] }) {
  return (
    <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {services.map((service) => {
        const state = STATE[service.status];
        return (
          <li
            key={service.key}
            className={cn(
              "rounded-xl border bg-white p-4 dark:bg-slate-900",
              service.status === "UP"
                ? "border-slate-200 dark:border-slate-800"
                : service.status === "DEGRADED"
                  ? "border-amber-300 dark:border-amber-500/40"
                  : "border-rose-300 dark:border-rose-500/40"
            )}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-medium text-slate-900 dark:text-slate-100">{service.name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">{service.role}</p>
              </div>
              <span className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium", state.pill)}>
                <span className={cn("h-1.5 w-1.5 rounded-full", state.dot)} aria-hidden />
                {state.label}
              </span>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2">
              {service.metrics.map((metric) => (
                <div key={metric.label} className="rounded-lg bg-slate-50 px-2.5 py-1.5 dark:bg-slate-800/60">
                  <dt className="text-[11px] text-slate-500 dark:text-slate-400">{metric.label}</dt>
                  <dd className="text-sm font-medium tabular-nums text-slate-900 dark:text-slate-100">{metric.value}</dd>
                </div>
              ))}
            </dl>
          </li>
        );
      })}
    </ul>
  );
}
