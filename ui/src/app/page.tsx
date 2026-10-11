import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ExternalLink, Lightbulb, MapPinned, Search } from "lucide-react";
import { TopNav } from "@/components/layout/TopNav";
import { PgsLogo } from "@/components/home/PgsLogo";
import { HomeSearch } from "@/components/home/HomeSearch";
import { ProvinceMap } from "@/components/home/ProvinceMap";

export const metadata: Metadata = {
  title: "PGS Search — Search Nepal’s public web by place",
};

// Only counts that are true of the boundary data shipped in public/data.
const STATS = [
  { value: "7", label: "Provinces" },
  { value: "77", label: "Districts" },
  { value: "753", label: "Local levels" },
];

export default function HomePage() {
  return (
    // font-sans: the app's body falls back to Arial; the home page uses the
    // Geist font the layout already loads.
    <div className="flex min-h-screen flex-col bg-white font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <main className="flex-1">
        {/* Hero */}
        <section className="relative isolate overflow-hidden border-b border-slate-200 bg-gradient-to-b from-blue-50 via-white to-white dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-950">
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-56 left-1/2 h-[34rem] w-[76rem] -translate-x-1/2 rounded-full bg-blue-200/45 blur-3xl dark:bg-blue-900/20" />
            <div className="absolute right-[8%] top-[42%] h-64 w-64 rounded-full bg-cyan-100/60 blur-3xl dark:bg-cyan-900/10" />
          </div>

          {/* The top bar sits on the hero's background, so there is no separate
              white strip above it. The big logo below is the brand here. */}
          <TopNav hideBrand />

          <div className="mx-auto max-w-7xl px-5 pb-12 pt-4 sm:px-6 sm:pb-16 sm:pt-8">
            <div className="text-center">
              <p className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white/80 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-blue-800 shadow-sm dark:border-blue-500/30 dark:bg-slate-900/80 dark:text-blue-300">
                <span className="h-2 w-2 rounded-full bg-blue-600 ring-4 ring-blue-100 dark:ring-blue-500/20" aria-hidden />
                The search engine for Nepal
              </p>
              {/* The colourful logo is the page's main heading. */}
              <h1 className="mt-5 flex justify-center">
                <PgsLogo />
              </h1>
              <p className="mx-auto mt-4 max-w-3xl text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
                Search news, government notices, universities and organisations across Nepal, with every result connected
                to its province, district and municipality.
              </p>
            </div>

            <div className="mt-9 grid grid-cols-1 items-stretch gap-5 lg:grid-cols-[0.9fr_1.1fr] lg:gap-6">
              <div id="search" className="scroll-mt-24 flex flex-col rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-xl shadow-blue-950/[0.04] backdrop-blur sm:p-8 dark:border-slate-800 dark:bg-slate-900/85">
                <div className="mb-5 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20">
                    <Search className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">Search</p>
                    <p className="text-base font-semibold text-slate-900 dark:text-slate-100">Find a topic, organisation or place</p>
                  </div>
                </div>
                <HomeSearch />
                <p className="mt-4 flex items-start gap-2 rounded-xl bg-slate-50 px-3 py-2.5 text-sm text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
                  <span>
                    Tip: type a district or province, like <b className="font-semibold text-slate-800 dark:text-slate-100">Kaski</b>, and pick it
                    from the list to open it on the map.
                  </span>
                </p>
                {/* Fills the extra height next to the taller map card, so the numbers sit at the bottom. */}
                <div className="hidden flex-1 lg:block" aria-hidden />
                <dl className="mt-7 grid grid-cols-3 divide-x divide-slate-200 border-t border-slate-200 pt-5 dark:divide-slate-700 dark:border-slate-700">
                  {STATS.map((stat) => (
                    <div key={stat.label} className="px-2 text-center first:pl-0 last:pr-0">
                      <dd className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl dark:text-white">{stat.value}</dd>
                      <dt className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {stat.label}
                      </dt>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-4 shadow-xl shadow-blue-950/[0.04] backdrop-blur sm:p-5 dark:border-slate-800 dark:bg-slate-900/85">
                <div className="mb-4 flex items-center justify-between gap-3 px-1">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">Or explore the map</p>
                    <p className="text-base font-semibold text-slate-900 dark:text-slate-100">Click a province to open it</p>
                  </div>
                  <Link
                    href="/map"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition-colors hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20"
                  >
                    Full map <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </div>
                <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-950/60">
                  <ProvinceMap />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Call to action */}
        <section className="mx-auto max-w-7xl px-5 py-14 sm:px-6 sm:py-16" aria-label="Get started">
          <div className="flex flex-col items-start justify-between gap-5 rounded-3xl bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-8 shadow-lg shadow-blue-600/20 sm:flex-row sm:items-center sm:px-10">
            <div>
              <p className="text-xl font-semibold text-white">Ready to explore?</p>
              <p className="mt-1 text-sm text-blue-100">Search for a topic, or open the map and click any district.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link
                href="#search"
                className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
              >
                <Search className="h-4 w-4" aria-hidden />
                Search now
              </Link>
              <Link
                href="/map"
                className="inline-flex items-center gap-2 rounded-lg border border-blue-300 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
              >
                <MapPinned className="h-4 w-4" aria-hidden />
                Open the map
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto grid max-w-7xl gap-8 px-5 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <p className="text-base font-semibold text-slate-900 dark:text-slate-100">PGS Search</p>
            <p className="mt-2 max-w-sm text-sm text-slate-600 dark:text-slate-400">
              A search engine for Nepal&rsquo;s public web, organised by place.
            </p>
          </div>
          <nav aria-label="Explore">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Explore</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <li>
                <Link href="#search" className="hover:text-slate-900 hover:underline dark:hover:text-white">
                  Search
                </Link>
              </li>
              <li>
                <Link href="/map" className="hover:text-slate-900 hover:underline dark:hover:text-white">
                  Geo Explorer
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-slate-900 hover:underline dark:hover:text-white">
                  Dashboard
                </Link>
              </li>
              <li>
                <Link href="/login" className="hover:text-slate-900 hover:underline dark:hover:text-white">
                  Sign in
                </Link>
              </li>
            </ul>
          </nav>
          <nav aria-label="Project">
            <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Project</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-400">
              <li>
                <a
                  href="https://github.com/tekraj/pgs-search-engine"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-slate-900 hover:underline dark:hover:text-white"
                >
                  Source code <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>
              </li>
              <li>
                <a
                  href="https://localboundries.oknp.org/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 hover:text-slate-900 hover:underline dark:hover:text-white"
                >
                  Map data: Open Knowledge Nepal <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                </a>
              </li>
            </ul>
          </nav>
        </div>
        <div className="border-t border-slate-200 dark:border-slate-800">
          <p className="mx-auto max-w-7xl px-5 py-4 text-xs text-slate-500 sm:px-6 dark:text-slate-400">
            © {new Date().getFullYear()} PGS Search · Boundary data CC BY 4.0, Open Knowledge Nepal
          </p>
        </div>
      </footer>
    </div>
  );
}
