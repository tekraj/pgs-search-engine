"use client";

import { useRouter } from "next/navigation";
import { MapPin } from "lucide-react";
import { DISTRICT_TO_PROVINCE, PROVINCE_NAMES, titleCase } from "@/lib/geo";
import { searchHref, type SearchState } from "@/components/search/url";

const PROVINCES = Object.values(PROVINCE_NAMES).map((p) => p.replace(" Province", ""));

// Location filters, matching the search API's province and district parameters.
export function SearchFilters({ state }: { state: SearchState }) {
  const router = useRouter();

  const districts = Object.entries(DISTRICT_TO_PROVINCE)
    .filter(([, province]) => !state.province || province.replace(" Province", "") === state.province)
    .map(([district]) => titleCase(district))
    .sort();

  const selectClass =
    "h-9 min-w-0 rounded-lg border border-slate-300 bg-white px-2.5 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200";

  return (
    <div className="flex flex-wrap items-center gap-2">
      <MapPin className="h-4 w-4 shrink-0 text-slate-400" aria-hidden />
      <label htmlFor="filter-province" className="sr-only">
        Province
      </label>
      <select
        id="filter-province"
        value={state.province ?? ""}
        onChange={(e) => {
          const province = e.target.value || undefined;
          // Keep the district only if it's in the newly chosen province.
          const keepDistrict =
            state.district &&
            province &&
            DISTRICT_TO_PROVINCE[state.district.toUpperCase()]?.replace(" Province", "") === province;
          router.push(searchHref(state, { province, district: keepDistrict ? state.district : undefined }));
        }}
        className={selectClass}
      >
        <option value="">All provinces</option>
        {PROVINCES.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>

      <label htmlFor="filter-district" className="sr-only">
        District
      </label>
      <select
        id="filter-district"
        value={state.district ?? ""}
        onChange={(e) => {
          const district = e.target.value || undefined;
          const province = district
            ? DISTRICT_TO_PROVINCE[district.toUpperCase()]?.replace(" Province", "")
            : state.province;
          router.push(searchHref(state, { district, province }));
        }}
        className={selectClass}
      >
        <option value="">{state.province ? `All districts in ${state.province}` : "All districts"}</option>
        {districts.map((d) => (
          <option key={d} value={d}>
            {d}
          </option>
        ))}
      </select>
    </div>
  );
}
