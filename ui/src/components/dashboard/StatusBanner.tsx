import { CircleAlert, CircleCheck, CircleX } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ServiceHealth } from "@/lib/mock/metrics";

// One sentence anyone can read: is the system OK, and if not, what does it mean
// for people using search?
export function StatusBanner({ services }: { services: ServiceHealth[] }) {
  const down = services.filter((s) => s.status === "DOWN");
  const degraded = services.filter((s) => s.status === "DEGRADED");

  const state = down.length > 0 ? "down" : degraded.length > 0 ? "degraded" : "ok";
  const affected = [...down, ...degraded].map((s) => s.name);

  const content = {
    ok: {
      icon: CircleCheck,
      title: "All systems are running normally",
      body: "Crawling, processing and search are all healthy.",
      classes: "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-100",
      iconClass: "text-emerald-600 dark:text-emerald-400",
    },
    degraded: {
      icon: CircleAlert,
      title: `${affected.length} service${affected.length === 1 ? " needs" : "s need"} attention: ${affected.join(", ")}`,
      body: "Search still works. New pages may take longer than usual to appear in results.",
      classes: "border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-100",
      iconClass: "text-amber-600 dark:text-amber-400",
    },
    down: {
      icon: CircleX,
      title: `${affected.length} service${affected.length === 1 ? " is" : "s are"} not working: ${affected.join(", ")}`,
      body: "Some parts of crawling or search are unavailable. Check the services below.",
      classes: "border-rose-200 bg-rose-50 text-rose-950 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-100",
      iconClass: "text-rose-600 dark:text-rose-400",
    },
  }[state];

  const Icon = content.icon;

  return (
    <div role="status" className={cn("flex items-start gap-3 rounded-xl border p-4", content.classes)}>
      <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", content.iconClass)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{content.title}</p>
        <p className="mt-0.5 text-sm opacity-80">{content.body}</p>
      </div>
      {state !== "ok" && (
        <a
          href="#services"
          className="hidden shrink-0 self-center rounded-md px-2 py-1 text-sm font-medium underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 sm:block"
        >
          View services
        </a>
      )}
    </div>
  );
}
