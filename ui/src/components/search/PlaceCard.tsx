import Link from "next/link";
import { ArrowRight, Filter, MapPinned } from "lucide-react";
import { getProvinceColor, titleCase } from "@/lib/geo";
import type { PlaceMatch } from "@/components/search/places";
import { searchHref, type SearchState } from "@/components/search/url";

const VISIBLE_LOCAL_GOVERNMENTS = 6;

// Shown when a search is about a place: what and where it is, and quick ways
// to see it on the map or narrow the results to it.
export function PlaceCard({ place, state }: { place: PlaceMatch; state: SearchState }) {
  const color = getProvinceColor(place.province);
  const shortProvince = place.province.replace(" Province", "");
  const kindLabel =
    place.kind === "province" ? "Province" : place.kind === "district" ? "District" : (place.level ?? "Local government");

  const filterChanges =
    place.kind === "province"
      ? { province: shortProvince, district: undefined }
      : { province: shortProvince, district: titleCase(place.district!) };
  const alreadyFiltered =
    state.province === filterChanges.province && (state.district ?? undefined) === filterChanges.district;

  return (
    <section
      aria-labelledby="place-card-title"
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="h-1.5" style={{ backgroundColor: color }} aria-hidden />
      <div className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{kindLabel}</p>
        <h2 id="place-card-title" className="mt-1 text-xl font-semibold text-slate-900 dark:text-slate-50">
          {place.name}
        </h2>
        {place.matchedAs && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">Also written &ldquo;{place.matchedAs}&rdquo;</p>
        )}

        <dl className="mt-4 space-y-2 text-sm">
          {place.kind !== "province" && (
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500 dark:text-slate-400">Province</dt>
              <dd className="flex items-center gap-1.5 font-medium text-slate-900 dark:text-slate-100">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} aria-hidden />
                {shortProvince}
              </dd>
            </div>
          )}
          {place.kind === "municipality" && place.district && (
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500 dark:text-slate-400">District</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">{titleCase(place.district)}</dd>
            </div>
          )}
          {place.kind === "province" && place.districtCount !== undefined && (
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500 dark:text-slate-400">Districts</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">{place.districtCount}</dd>
            </div>
          )}
          {place.localGovernments && (
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500 dark:text-slate-400">Local governments</dt>
              <dd className="font-medium text-slate-900 dark:text-slate-100">{place.localGovernments.length}</dd>
            </div>
          )}
        </dl>

        {place.localGovernments && place.localGovernments.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-1.5" aria-label={`Local governments in ${place.name}`}>
            {place.localGovernments.slice(0, VISIBLE_LOCAL_GOVERNMENTS).map((lg) => (
              <li key={lg.name}>
                <Link
                  href={searchHref(state, { q: lg.name })}
                  title={lg.level}
                  className="inline-block rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                >
                  {lg.name}
                </Link>
              </li>
            ))}
            {place.localGovernments.length > VISIBLE_LOCAL_GOVERNMENTS && (
              <li className="px-1 py-1 text-xs text-slate-500 dark:text-slate-400">
                +{place.localGovernments.length - VISIBLE_LOCAL_GOVERNMENTS} more on the map
              </li>
            )}
          </ul>
        )}

        <div className="mt-5 flex flex-col gap-2">
          <Link
            href={place.mapHref}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900"
          >
            <MapPinned className="h-4 w-4" aria-hidden />
            View on map
          </Link>
          {!alreadyFiltered && (
            <Link
              href={searchHref(state, filterChanges)}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <Filter className="h-4 w-4" aria-hidden />
              Only results from {place.kind === "province" ? shortProvince : place.kind === "district" ? place.name : titleCase(place.district!)}
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          )}
        </div>
      </div>
    </section>
  );
}
