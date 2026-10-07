"use client";

import { cn } from "@/lib/cn";
import { useState } from "react";

const TABS = ["All", "Places", "News", "Images"];

export function SearchTabs() {
  const [active, setActive] = useState("All");
  return (
    <div
      role="group"
      aria-label="Result type"
      className="flex gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
    >
      {TABS.map((tab) => (
        <button
          key={tab}
          type="button"
          onClick={() => setActive(tab)}
          aria-pressed={active === tab}
          className={cn(
            "-mb-px shrink-0 border-b-2 px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500",
            active === tab
              ? "border-blue-600 text-blue-700 dark:border-blue-400 dark:text-blue-400"
              : "border-transparent text-slate-600 hover:border-slate-300 hover:text-slate-900 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-slate-100"
          )}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}
