import { TopNav } from "@/components/layout/TopNav";
import { DemoNewsMap } from "@/components/map/DemoNewsMap";

export default function DistrictNewsDemoPage() {
  return (
    <div className="flex h-screen flex-col bg-white dark:bg-slate-950">
      <div className="shrink-0 border-b border-slate-200 dark:border-slate-800">
        <TopNav />
      </div>
      <div className="min-h-0 flex-1">
        <DemoNewsMap />
      </div>
    </div>
  );
}
