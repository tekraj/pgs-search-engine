"use client";

import { useRouter } from "next/navigation";
import { useId, useMemo, useState } from "react";
import { MapPin, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { DISTRICT_ALIASES, DISTRICT_TO_PROVINCE, PROVINCE_NAMES, titleCase } from "@/lib/geo";

interface Suggestion {
  kind: "search" | "place";
  label: string;
  detail: string;
  href: string;
}

const EXAMPLES = ["Lok Sewa notices", "Kathmandu budget", "Pokhara", "University results"];

const PROVINCES = Object.values(PROVINCE_NAMES);
const DISTRICTS = Object.keys(DISTRICT_TO_PROVINCE);

// Places whose name (or a common short name / old spelling) matches the query,
// best matches first: names that start with it before names that contain it.
function matchPlaces(query: string): Suggestion[] {
  const q = query.toLowerCase();
  const ranked: { score: number; suggestion: Suggestion }[] = [];

  for (const province of PROVINCES) {
    const short = province.replace(" Province", "");
    const name = short.toLowerCase();
    if (!name.includes(q)) continue;
    ranked.push({
      score: name.startsWith(q) ? 0 : 2,
      suggestion: { kind: "place", label: short, detail: "Province", href: `/map?focus=${encodeURIComponent(short)}` },
    });
  }
  for (const district of DISTRICTS) {
    const name = district.toLowerCase();
    const alias = DISTRICT_ALIASES[district]?.find((a) => a.toLowerCase().includes(q));
    if (!name.includes(q) && !alias) continue;
    const display = titleCase(district);
    ranked.push({
      score: name.startsWith(q) ? 1 : alias?.toLowerCase().startsWith(q) ? 1 : 3,
      suggestion: {
        kind: "place",
        label: alias && !name.includes(q) ? `${display} (${alias})` : display,
        detail: `District · ${DISTRICT_TO_PROVINCE[district].replace(" Province", "")}`,
        href: `/map?focus=${encodeURIComponent(display)}`,
      },
    });
  }
  return ranked
    .sort((a, b) => a.score - b.score || a.suggestion.label.localeCompare(b.suggestion.label))
    .slice(0, 5)
    .map((r) => r.suggestion);
}

export function HomeSearch() {
  const router = useRouter();
  const listboxId = useId();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const suggestions = useMemo<Suggestion[]>(() => {
    const q = query.trim();
    if (!q) return [];
    return [
      { kind: "search", label: `Search for “${q}”`, detail: "Web results", href: `/search?q=${encodeURIComponent(q)}` },
      ...matchPlaces(q),
    ];
  }, [query]);

  const showList = open && suggestions.length > 0;

  function go(href: string) {
    setOpen(false);
    router.push(href);
  }

  function submit(q: string) {
    const trimmed = q.trim();
    if (trimmed) go(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <div className="w-full">
      <form
        role="search"
        onSubmit={(e) => {
          e.preventDefault();
          if (showList && active >= 0) go(suggestions[active].href);
          else submit(query);
        }}
        className="relative"
      >
        <label htmlFor="home-search" className="sr-only">
          Search the Nepali web, or find a place
        </label>
        <div className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white p-1.5 pl-4 shadow-sm transition-shadow focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-500/15 dark:border-slate-700 dark:bg-slate-900">
          <Search className="h-5 w-5 shrink-0 text-slate-400" aria-hidden />
          <input
            id="home-search"
            type="search"
            role="combobox"
            aria-expanded={showList}
            aria-controls={listboxId}
            aria-autocomplete="list"
            aria-activedescendant={showList && active >= 0 ? `${listboxId}-${active}` : undefined}
            autoComplete="off"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              setActive(-1);
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 120)}
            onKeyDown={(e) => {
              if (!showList) return;
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((i) => (i + 1) % suggestions.length);
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
              } else if (e.key === "Escape") {
                setOpen(false);
              }
            }}
            placeholder="Search news, notices, offices, or a place like “Kaski”"
            className="h-11 min-w-0 flex-1 bg-transparent text-base text-slate-900 outline-none placeholder:text-slate-400 dark:text-slate-100 [&::-webkit-search-cancel-button]:hidden"
          />
          <button
            type="submit"
            className="h-11 shrink-0 rounded-lg bg-blue-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900"
          >
            Search
          </button>
        </div>

        {showList && (
          <ul
            id={listboxId}
            role="listbox"
            aria-label="Suggestions"
            className="absolute inset-x-0 top-full z-30 mt-2 overflow-hidden rounded-xl border border-slate-200 bg-white py-1.5 shadow-lg dark:border-slate-700 dark:bg-slate-900"
          >
            {suggestions.map((s, i) => (
              <li
                key={s.href}
                id={`${listboxId}-${i}`}
                role="option"
                aria-selected={i === active}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => go(s.href)}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  "flex cursor-pointer items-center gap-3 px-4 py-2.5 text-sm",
                  i === active ? "bg-slate-100 dark:bg-slate-800" : ""
                )}
              >
                {s.kind === "search" ? (
                  <Search className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                ) : (
                  <MapPin className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
                )}
                <span className="min-w-0 flex-1 truncate text-slate-900 dark:text-slate-100">{s.label}</span>
                <span className="shrink-0 text-xs text-slate-500 dark:text-slate-400">
                  {s.kind === "place" ? `${s.detail} · on map` : s.detail}
                </span>
              </li>
            ))}
          </ul>
        )}
      </form>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <span className="text-slate-500 dark:text-slate-400">Try:</span>
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => submit(example)}
            className="rounded-full border border-slate-200 bg-white px-3 py-1 text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
