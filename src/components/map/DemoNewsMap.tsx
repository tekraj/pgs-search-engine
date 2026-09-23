"use client";

import dynamic from "next/dynamic";

const DemoNewsMapView = dynamic(
  () => import("@/components/map/DemoNewsMapView").then((m) => m.DemoNewsMapView),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center text-sm text-slate-400">
        Loading map…
      </div>
    ),
  }
);

export function DemoNewsMap() {
  return <DemoNewsMapView />;
}
