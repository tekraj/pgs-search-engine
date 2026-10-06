import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import type { NodeMetrics } from "@/lib/mock/metrics";

function usageTone(value: number) {
  if (value >= 90) return { bar: "bg-rose-500", text: "text-rose-700 dark:text-rose-400" };
  if (value >= 75) return { bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" };
  return { bar: "bg-emerald-500", text: "text-slate-700 dark:text-slate-300" };
}

function UsageBar({ value, label, detail }: { value: number; label: string; detail?: string }) {
  const tone = usageTone(value);
  return (
    <div className="min-w-[7rem]">
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className={cn("font-medium tabular-nums", tone.text)}>{Math.round(value)}%</span>
        {detail && <span className="text-slate-400">{detail}</span>}
      </div>
      <div
        className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"
        role="meter"
        aria-label={label}
        aria-valuenow={Math.round(value)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={cn("h-full rounded-full", tone.bar)} style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

export function NodesTable({ nodes }: { nodes: NodeMetrics[] }) {
  const busy = nodes.filter((n) => n.cpu_usage_percent >= 90 || n.ram_usage.percent >= 90).length;

  return (
    <Card>
      <CardHeader
        title="Servers"
        subtitle={
          busy > 0
            ? `${nodes.length} servers · ${busy} running above 90% (shown in red)`
            : `${nodes.length} servers · all within normal limits`
        }
      />
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead className="text-xs text-slate-500 dark:text-slate-400">
            <tr className="border-b border-slate-200 dark:border-slate-800">
              <th scope="col" className="px-4 py-2 font-medium">Server</th>
              <th scope="col" className="px-4 py-2 font-medium">Status</th>
              <th scope="col" className="px-4 py-2 font-medium">CPU</th>
              <th scope="col" className="px-4 py-2 font-medium">Memory</th>
              <th scope="col" className="px-4 py-2 text-right font-medium">Pods</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {nodes.map((node) => (
              <tr key={node.node_name}>
                <th scope="row" className="px-4 py-3 font-normal">
                  <p className="font-mono text-[13px] font-medium text-slate-900 dark:text-slate-100">{node.node_name}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{node.role}</p>
                </th>
                <td className="px-4 py-3">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 text-xs font-medium",
                      node.status === "Ready" ? "text-emerald-700 dark:text-emerald-400" : "text-rose-700 dark:text-rose-400"
                    )}
                  >
                    <span
                      className={cn("h-1.5 w-1.5 rounded-full", node.status === "Ready" ? "bg-emerald-500" : "bg-rose-500")}
                      aria-hidden
                    />
                    {node.status === "Ready" ? "Ready" : "Not ready"}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <UsageBar value={node.cpu_usage_percent} label={`${node.node_name} CPU`} />
                </td>
                <td className="px-4 py-3">
                  <UsageBar
                    value={node.ram_usage.percent}
                    label={`${node.node_name} memory`}
                    detail={`${node.ram_usage.used_gb} / ${node.ram_usage.total_gb} GB`}
                  />
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-700 dark:text-slate-300">{node.running_pods}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
