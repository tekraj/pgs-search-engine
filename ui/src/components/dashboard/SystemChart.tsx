"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardHeader } from "@/components/ui/Card";
import { cn } from "@/lib/cn";
import { formatClock } from "@/components/dashboard/format";
import { generateMetricSeries, nextMetricPoint } from "@/lib/mock/metrics";
import type { MetricPoint } from "@/lib/types";

type View = "load" | "traffic";

const VIEWS: Record<
  View,
  { label: string; series: { key: keyof MetricPoint; name: string; color: string; unit: string }[] }
> = {
  load: {
    label: "CPU & memory",
    series: [
      { key: "cpu", name: "CPU", color: "#2563eb", unit: "%" },
      { key: "ram", name: "Memory", color: "#16a34a", unit: "%" },
    ],
  },
  traffic: {
    label: "Search traffic",
    series: [
      { key: "queriesPerSec", name: "Searches / sec", color: "#7c3aed", unit: "" },
      { key: "latencyMs", name: "Response time", color: "#d97706", unit: " ms" },
    ],
  },
};

const UPDATE_MS = 5000;

export function SystemChart() {
  const [data, setData] = useState<MetricPoint[]>([]);
  const [view, setView] = useState<View>("load");

  useEffect(() => {
    // Generated after mount so server and browser render the same initial HTML.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setData(generateMetricSeries());
    const interval = setInterval(() => {
      // No need to animate a chart nobody is looking at.
      if (document.hidden) return;
      setData((prev) => (prev.length ? [...prev.slice(1), nextMetricPoint(prev[prev.length - 1])] : prev));
    }, UPDATE_MS);
    return () => clearInterval(interval);
  }, []);

  const config = VIEWS[view];
  const latest = data[data.length - 1];

  return (
    <Card>
      <CardHeader
        title="Cluster load"
        subtitle="Last hour · all nodes · live"
        action={
          <div role="group" aria-label="Chart" className="flex shrink-0 rounded-lg bg-slate-100 p-0.5 dark:bg-slate-800">
            {(Object.keys(VIEWS) as View[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setView(key)}
                aria-pressed={view === key}
                className={cn(
                  "rounded-md px-2.5 py-1 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
                  view === key
                    ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-50"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                )}
              >
                {VIEWS[key].label}
              </button>
            ))}
          </div>
        }
      />

      {/* Current values, readable without the chart. */}
      <dl className="flex flex-wrap gap-x-6 gap-y-2 px-4 pt-4">
        {config.series.map((s) => (
          <div key={s.key} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} aria-hidden />
            <dt className="text-sm text-slate-600 dark:text-slate-400">{s.name}</dt>
            <dd className="text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
              {latest ? `${latest[s.key]}${s.unit}` : "—"}
            </dd>
          </div>
        ))}
      </dl>

      <div className="h-64 p-2 pr-4 sm:p-4" aria-hidden>
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
              <defs>
                {config.series.map((s) => (
                  <linearGradient key={s.key} id={`fill-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={s.color} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={s.color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-slate-200 dark:stroke-slate-800" />
              <XAxis
                dataKey="time"
                tickFormatter={(t: string) => formatClock(t)}
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
                minTickGap={32}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                stroke="#94a3b8"
                width={36}
                domain={view === "load" ? [0, 100] : [0, "auto"]}
                unit={view === "load" ? "%" : ""}
              />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
                labelFormatter={(t) => `${formatClock(String(t))} NPT`}
                formatter={(value, name) => {
                  const s = config.series.find((x) => x.name === name);
                  return [`${value}${s?.unit ?? ""}`, name];
                }}
              />
              {config.series.map((s) => (
                <Area
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.name}
                  stroke={s.color}
                  fill={`url(#fill-${s.key})`}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
        )}
      </div>
    </Card>
  );
}
