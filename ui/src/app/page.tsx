import Link from "next/link";
import {
  ArrowRight,
  Building2,
  ExternalLink,
  Globe,
  GraduationCap,
  Landmark,
  LayoutDashboard,
  MapPin,
  MapPinned,
  Newspaper,
  Radar,
  ScanSearch,
  Search,
  Tags,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { TopNav } from "@/components/layout/TopNav";
import { HomeSearch } from "@/components/home/HomeSearch";
import { ProvinceMap } from "@/components/home/ProvinceMap";
import { DISTRICT_TO_PROVINCE, PROVINCE_NAMES, getProvinceColor } from "@/lib/geo";

// Only counts that are true of the data shipped in public/data — no invented
// document totals while the index itself is still mock data.
const STATS = [
  { value: "7", label: "Provinces" },
  { value: "77", label: "Districts" },
  { value: "753", label: "Local levels" },
];

const FEATURES: { icon: LucideIcon; title: string; body: string; href: string; cta: string }[] = [
  {
    icon: Search,
    title: "Search the Nepali web",
    body: "One search across news portals, government offices, universities and organisations in Nepal.",
    href: "#search",
    cta: "Start searching",
  },
  {
    icon: MapPinned,
    title: "Explore by map",
    body: "Drill down from province to district to municipality, with every local government named on the map.",
    href: "/map",
    cta: "Open the map",
  },
  {
    icon: Newspaper,
    title: "Local news by district",
    body: "Click any district or municipality on the map to see the latest news from that area.",
    href: "/map",
    cta: "Find local news",
  },
  {
    icon: MapPin,
    title: "Save places with pins",
    body: "Drop a pin anywhere in Nepal, give it a name and a note, and find it again later.",
    href: "/map",
    cta: "Drop a pin",
  },
  {
    icon: Tags,
    title: "Results tied to places",
    body: "Pages are tagged to the province, district and municipality they’re about, so you can search by place.",
    href: "/search?q=Pokhara",
    cta: "See an example",
  },
  {
    icon: LayoutDashboard,
    title: "Operations dashboard",
    body: "For the team running PGS: system health, crawl results and logs in one place. Sign-in required.",
    href: "/dashboard",
    cta: "Go to dashboard",
  },
];

const SOURCES: { icon: LucideIcon; title: string; body: string; query: string }[] = [
  { icon: Newspaper, title: "News portals", body: "National and local news sites", query: "Nepal news" },
  {
    icon: Landmark,
    title: "Government",
    body: "Federal ministries, provinces, municipalities and wards",
    query: "government notice",
  },
  {
    icon: GraduationCap,
    title: "Education",
    body: "Universities, colleges and exam results",
    query: "university results",
  },
  {
    icon: Building2,
    title: "Organisations",
    body: "Banks, companies and cooperatives",
    query: "bank interest rates",
  },
  { icon: Globe, title: "Other .np sites", body: "Public websites based in Nepal", query: "np websites" },
];

const STEPS: { icon: LucideIcon; title: string; body: string }[] = [
  {
    icon: Radar,
    title: "Crawl",
    body: "A fleet of crawlers visits public Nepali websites and collects their pages and documents.",
  },
  {
    icon: Tags,
    title: "Understand",
    body: "Nepali and English text is extracted, and each page is tagged to the place it’s about.",
  },
  {
    icon: ScanSearch,
    title: "Search",
    body: "Results are ranked by both keywords and meaning, shown as a list or on the map.",
  },
];

const PROVINCES = Object.values(PROVINCE_NAMES).map((name) => ({
  name,
  shortName: name.replace(" Province", ""),
  color: getProvinceColor(name),
  districts: Object.values(DISTRICT_TO_PROVINCE).filter((p) => p === name).length,
}));

function SectionHeading({ eyebrow, title, body }: { eyebrow: string; title: string; body?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-sm font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-400">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl dark:text-slate-50">
        {title}
      </h2>
      {body && <p className="mt-3 text-base text-slate-600 dark:text-slate-400">{body}</p>}
    </div>
  );
}

const CARD =
  "rounded-2xl border border-slate-200 bg-white transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-800 dark:bg-slate-900";

export default function HomePage() {
  return (
    // font-sans: the app's body falls back to Arial; the home page uses the
    // Geist font the layout already loads.
    <div className="flex min-h-screen flex-col bg-white font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <TopNav />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative isolate overflow-hidden border-b border-slate-200 bg-gradient-to-b from-blue-50 via-white to-white dark:border-slate-800 dark:from-slate-900 dark:via-slate-950 dark:to-slate-950">
          <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
            <div className="absolute -top-56 left-1/2 h-[34rem] w-[76rem] -translate-x-1/2 rounded-full bg-blue-200/45 blur-3xl dark:bg-blue-900/20" />
            <div className="absolute right-[8%] top-[42%] h-64 w-64 rounded-full bg-cyan-100/60 blur-3xl dark:bg-cyan-900/10" />
          </div>

          <div className="mx-auto max-w-7xl px-5 pb-12 pt-12 sm:px-6 sm:pb-16 sm:pt-16">
            <div className="text-center">
              <p className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white/80 px-3.5 py-1.5 text-xs font-semibold tracking-wide text-blue-800 shadow-sm dark:border-blue-500/30 dark:bg-slate-900/80 dark:text-blue-300">
                <span className="h-2 w-2 rounded-full bg-blue-600 ring-4 ring-blue-100 dark:ring-blue-500/20" aria-hidden />
                The search engine for Nepal
              </p>
              <h1 className="mx-auto mt-5 text-[clamp(2rem,3.2vw,3.5rem)] font-semibold leading-tight tracking-[-0.04em] text-slate-950 dark:text-white lg:whitespace-nowrap">
                Find what&rsquo;s published in Nepal <span className="text-blue-700 dark:text-blue-400">&mdash; by place.</span>
              </h1>
              <p className="mx-auto mt-4 max-w-3xl text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
                Search news, government notices, universities and organisations across Nepal, with every result connected
                to its province, district and municipality.
              </p>
            </div>

            <div className="mt-9 grid grid-cols-1 items-stretch gap-5 lg:grid-cols-[0.9fr_1.1fr] lg:gap-6">
              <div id="search" className="scroll-mt-24 flex flex-col justify-center rounded-3xl border border-slate-200/80 bg-white/90 p-5 shadow-xl shadow-blue-950/[0.04] backdrop-blur sm:p-8 dark:border-slate-800 dark:bg-slate-900/85">
                <div className="mb-5 flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md shadow-blue-600/20">
                    <Search className="h-5 w-5" aria-hidden />
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Search across Nepal</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Find a topic, organisation or place</p>
                  </div>
                </div>
                <HomeSearch />
                <dl className="mt-7 grid grid-cols-3 divide-x divide-slate-200 border-t border-slate-200 pt-5 dark:divide-slate-700 dark:border-slate-700">
                  {STATS.map((stat) => (
                    <div key={stat.label} className="px-2 text-center first:pl-0 last:pr-0">
                      <dd className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl dark:text-white">{stat.value}</dd>
                      <dt className="mt-1 text-[0.65rem] font-medium uppercase tracking-wide text-slate-500 sm:text-xs dark:text-slate-400">
                        {stat.label}
                      </dt>
                    </div>
                  ))}
                </dl>
              </div>

              <div className="overflow-hidden rounded-3xl border border-slate-200/80 bg-white/90 p-4 shadow-xl shadow-blue-950/[0.04] backdrop-blur sm:p-5 dark:border-slate-800 dark:bg-slate-900/85">
                <div className="mb-4 flex items-center justify-between gap-3 px-1">
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">Explore Nepal by province</p>
                    <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Select a province to open the map</p>
                  </div>
                  <Link
                    href="/map"
                    className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-semibold text-blue-700 transition-colors hover:bg-blue-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:bg-blue-500/20"
                  >
                    Full map <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </Link>
                </div>
                <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-100">
                  <ProvinceMap />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto max-w-6xl px-6 py-16 sm:py-20" aria-labelledby="features-heading">
          <div id="features-heading">
            <SectionHeading
              eyebrow="What you can do"
              title="Everything about Nepal’s public web, in one place"
              body="Search it as a list, or explore it as a map — whichever fits what you’re looking for."
            />
          </div>
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <li key={feature.title}>
                <Link href={feature.href} className={`group flex h-full flex-col p-6 ${CARD}`}>
                  <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                    <feature.icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-slate-100">{feature.title}</h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{feature.body}</p>
                  <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-blue-700 dark:text-blue-400">
                    {feature.cta}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* Sources */}
        <section
          className="border-y border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50"
          aria-labelledby="sources-heading"
        >
          <div className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
            <div id="sources-heading">
              <SectionHeading
                eyebrow="What PGS searches"
                title="Beyond the news"
                body="PGS covers the whole public Nepali web — from ministries and ward offices to universities and banks."
              />
            </div>
            <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {SOURCES.map((source) => (
                <li key={source.title}>
                  <Link
                    href={`/search?q=${encodeURIComponent(source.query)}`}
                    className={`group flex h-full flex-col p-5 ${CARD}`}
                  >
                    <source.icon className="h-6 w-6 text-slate-700 dark:text-slate-300" aria-hidden />
                    <h3 className="mt-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{source.title}</h3>
                    <p className="mt-1 flex-1 text-sm text-slate-600 dark:text-slate-400">{source.body}</p>
                    <span className="mt-3 text-xs font-medium text-blue-700 group-hover:underline dark:text-blue-400">
                      Search {source.title.toLowerCase()}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Provinces */}
        <section className="mx-auto max-w-6xl px-6 py-16 sm:py-20" aria-labelledby="provinces-heading">
          <div id="provinces-heading">
            <SectionHeading
              eyebrow="Explore by place"
              title="Start from a province"
              body="Each province opens on the map with its districts, local governments and local news."
            />
          </div>
          <ul className="mt-10 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {PROVINCES.map((province) => (
              <li key={province.name}>
                <Link
                  href={`/map?focus=${encodeURIComponent(province.shortName)}`}
                  className={`group flex items-center gap-3 p-4 ${CARD}`}
                >
                  <span
                    className="h-9 w-9 shrink-0 rounded-lg"
                    style={{ backgroundColor: province.color }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {province.shortName}
                    </span>
                    <span className="block text-xs text-slate-500 dark:text-slate-400">
                      {province.districts} districts
                    </span>
                  </span>
                  <ArrowRight
                    className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-hover:translate-x-0.5"
                    aria-hidden
                  />
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/map"
                className={`flex h-full items-center justify-center gap-2 p-4 text-sm font-semibold text-blue-700 dark:text-blue-400 ${CARD}`}
              >
                All of Nepal <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </li>
          </ul>
        </section>

        {/* How it works */}
        <section
          className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50"
          aria-labelledby="how-heading"
        >
          <div className="mx-auto max-w-6xl px-6 py-16 sm:py-20">
            <div id="how-heading">
              <SectionHeading eyebrow="How it works" title="From a web page to a place on the map" />
            </div>
            <ol className="mt-10 grid gap-6 md:grid-cols-3">
              {STEPS.map((step, i) => (
                <li key={step.title} className="relative rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
                      {i + 1}
                    </span>
                    <step.icon className="h-5 w-5 text-slate-500 dark:text-slate-400" aria-hidden />
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-slate-900 dark:text-slate-100">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{step.body}</p>
                </li>
              ))}
            </ol>

            <div className="mt-12 flex flex-col items-start justify-between gap-4 rounded-2xl bg-blue-600 px-6 py-8 sm:flex-row sm:items-center sm:px-8">
              <div>
                <p className="text-lg font-semibold text-white">Ready to explore?</p>
                <p className="mt-1 text-sm text-blue-100">Search for anything, or start from the map of Nepal.</p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="#search"
                  className="rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
                >
                  Search now
                </Link>
                <Link
                  href="/map"
                  className="rounded-lg border border-blue-300 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
                >
                  Open the map
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 sm:grid-cols-2 lg:grid-cols-4">
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
          <p className="mx-auto max-w-6xl px-6 py-4 text-xs text-slate-500 dark:text-slate-400">
            © {new Date().getFullYear()} PGS Search · Boundary data CC BY 4.0, Open Knowledge Nepal
          </p>
        </div>
      </footer>
    </div>
  );
}
