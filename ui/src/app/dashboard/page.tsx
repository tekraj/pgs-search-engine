import { Database, FileStack, Globe, HardDrive } from "lucide-react";
import { Section } from "@/components/dashboard/Section";
import { StatusBanner } from "@/components/dashboard/StatusBanner";
import { StatCard } from "@/components/dashboard/StatCard";
import { RefreshButton } from "@/components/dashboard/RefreshButton";
import { PipelineFlow } from "@/components/dashboard/PipelineFlow";
import { ServiceHealth } from "@/components/dashboard/ServiceHealth";
import { SystemChart } from "@/components/dashboard/SystemChart";
import { NodesTable } from "@/components/dashboard/NodesTable";
import { DomainsTable } from "@/components/dashboard/DomainsTable";
import { LogStream } from "@/components/dashboard/LogStream";
import { QuarantineList } from "@/components/dashboard/QuarantineList";
import { formatClock, formatCompact, formatNumber } from "@/components/dashboard/format";
import { getSessionUser } from "@/lib/auth/session";
import {
  getDomains,
  getErrorLogs,
  getNodes,
  getQuarantine,
  getServices,
  getStorage,
  getSummary,
} from "@/lib/mock/metrics";

// Sample data for now; each call maps to one admin API endpoint (see
// lib/mock/metrics.ts), so this is the one place to switch to real fetches.
async function loadDashboard() {
  const now = Date.now();
  return {
    now,
    summary: getSummary(now),
    services: getServices(),
    nodes: getNodes(),
    domains: getDomains(now),
    storage: getStorage(now),
    logs: getErrorLogs(now),
    quarantine: getQuarantine(now),
  };
}

export default async function DashboardPage() {
  const user = await getSessionUser();
  const { now, summary, services, nodes, domains, storage, logs, quarantine } = await loadDashboard();
  const runningServices = services.filter((s) => s.status === "UP").length;
  const { infrastructure: infra } = summary;

  return (
    <div className="space-y-10">
      <Section
        id="overview"
        title={`Welcome back${user ? `, ${user.name}` : ""}`}
        description={`Here's how the search engine is doing. Updated ${formatClock(summary.timestamp)} NPT.`}
        action={
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800 dark:bg-amber-500/10 dark:text-amber-300">
              Sample data
            </span>
            <RefreshButton />
          </div>
        }
      >
        <div className="space-y-4">
          <StatusBanner services={services} />
          <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
            <StatCard
              label="Websites tracked"
              value={formatNumber(summary.domains.total_registered)}
              hint={`${formatNumber(summary.domains.active_crawling)} crawling now · ${formatNumber(summary.domains.failed_or_blocked)} failed or blocked`}
              icon={Globe}
              tone="blue"
            />
            <StatCard
              label="Documents in search"
              value={formatCompact(summary.storage.processed_files)}
              hint="Pages and files people can find"
              icon={FileStack}
              tone="emerald"
            />
            <StatCard
              label="Links waiting"
              value={formatCompact(summary.links.queued_for_crawl)}
              hint="Queued to be crawled next"
              icon={Database}
              tone="amber"
            />
            <StatCard
              label="Storage used"
              value={summary.storage.formatted_storage}
              hint={`${formatCompact(summary.storage.total_raw_files_disk)} downloaded files`}
              icon={HardDrive}
              tone="violet"
            />
          </div>
        </div>
      </Section>

      <Section
        id="pipeline"
        title="Pipeline"
        description="How a web page becomes a search result, and how much is waiting at each step."
      >
        <PipelineFlow summary={summary} storage={storage} now={now} />
      </Section>

      <Section
        id="services"
        title="Services"
        description={`${runningServices} of ${services.length} services running normally.`}
      >
        <ServiceHealth services={services} />
      </Section>

      <Section
        id="infrastructure"
        title="Infrastructure"
        description={`${infra.k8s_active_nodes} Kubernetes nodes · ${infra.temporal_worker_pods} crawler pods · ${infra.spark_executors} Spark executors · ${infra.kafka_brokers} Kafka brokers`}
      >
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <SystemChart />
          <NodesTable nodes={nodes} />
        </div>
      </Section>

      <Section id="domains" title="Websites" description="The sites the crawler visits. Search, filter, and pause or re-crawl a site.">
        <DomainsTable
          domains={domains}
          totalRegistered={summary.domains.total_registered}
          now={now}
          canManage={user?.role === "admin"}
        />
      </Section>

      <Section id="logs" title="Logs" description="What the services are reporting right now.">
        <LogStream initialLogs={logs} />
      </Section>

      <Section id="security" title="Security" description="Files blocked by the virus scanner before they could be indexed.">
        <QuarantineList files={quarantine} store={storage.quarantine_store} now={now} />
      </Section>
    </div>
  );
}
