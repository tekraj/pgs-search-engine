// Server-side only (reads public/data from disk); used by the search page.
import fs from "node:fs/promises";
import path from "node:path";
import {
  DISTRICT_ALIASES,
  DISTRICT_TO_PROVINCE,
  PROVINCE_NAMES,
  getLevelLabel,
  titleCase,
  type MunicipalityCollection,
} from "@/lib/geo";

// Works out which place a search is about ("pokhara budget", "kavre", "Gandaki
// jobs") using the same boundary data as the map, so search can show a place
// card and tag results to it.

export interface LocalGovernment {
  name: string;
  level: string;
}

export interface PlaceMatch {
  kind: "province" | "district" | "municipality";
  name: string;
  province: string;
  /** District key as stored in the data, e.g. "KASKI". */
  district?: string;
  /** Plain-English level for a municipality, e.g. "Metropolitan city". */
  level?: string;
  /** The spelling the user typed when it differs from the official one. */
  matchedAs?: string;
  districtCount?: number;
  localGovernments?: LocalGovernment[];
  mapHref: string;
}

interface MunicipalityRecord {
  name: string;
  district: string;
  level: string;
}

const PROTECTED_AREA = /park|reserve|development area/i;

let municipalitiesPromise: Promise<MunicipalityRecord[]> | null = null;

function loadMunicipalities() {
  municipalitiesPromise ??= (async () => {
    const file = path.join(process.cwd(), "public", "data", "nepal-municipalities.geojson");
    const data = JSON.parse(await fs.readFile(file, "utf8")) as MunicipalityCollection;
    const seen = new Set<string>();
    const records: MunicipalityRecord[] = [];
    for (const f of data.features) {
      const { N_ID, NAME, DISTRICT, LEVEL } = f.properties;
      if (!NAME || !N_ID || seen.has(N_ID)) continue;
      seen.add(N_ID);
      records.push({ name: NAME, district: DISTRICT, level: LEVEL });
    }
    return records;
  })();
  return municipalitiesPromise;
}

function containsWords(haystack: string, needle: string): boolean {
  const escaped = needle.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^a-z])${escaped}($|[^a-z])`).test(haystack);
}

function short(province: string) {
  return province.replace(" Province", "");
}

async function localGovernmentsIn(district: string): Promise<LocalGovernment[]> {
  return (await loadMunicipalities())
    .filter((m) => m.district === district && !PROTECTED_AREA.test(m.level))
    .map((m) => ({ name: m.name, level: getLevelLabel(m.level) }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

export async function findPlace(query: string): Promise<PlaceMatch | null> {
  const q = query.toLowerCase().trim();
  if (q.length < 3) return null;

  // Districts first (official name or a known short name / old spelling),
  // preferring the longest match: "Nawalparasi East" over "Nawalparasi".
  let districtHit: { district: string; matchedAs?: string; length: number } | null = null;
  for (const district of Object.keys(DISTRICT_TO_PROVINCE)) {
    const spellings = [district, ...(DISTRICT_ALIASES[district] ?? [])];
    for (const spelling of spellings) {
      if (spelling.length >= 3 && containsWords(q, spelling) && (!districtHit || spelling.length > districtHit.length)) {
        districtHit = {
          district,
          matchedAs: spelling === district ? undefined : spelling,
          length: spelling.length,
        };
      }
    }
  }

  const provinceHit = Object.values(PROVINCE_NAMES).find((p) => containsWords(q, short(p)));

  // A municipality whose full name is in the query, or — when no district
  // matched — whose distinctive first word is ("Pokhara" → Pokhara Lekhnath).
  // The first-word rule skips parks and reserves, so "Chitawan" means the
  // district, not Chitawan National Park. Names shared by several districts
  // (e.g. Madi, in four) only count when the district is also in the query.
  const municipalities = await loadMunicipalities();
  const candidates = municipalities.filter((m) => {
    const name = m.name.toLowerCase();
    if (containsWords(q, name)) return true;
    const firstWord = name.split(" ")[0];
    return !districtHit && !PROTECTED_AREA.test(m.level) && firstWord.length >= 5 && containsWords(q, firstWord);
  });
  const inDistrict = districtHit ? candidates.filter((m) => m.district === districtHit!.district) : candidates;
  const unambiguous = new Set(inDistrict.map((m) => m.district)).size === 1 ? inDistrict : [];
  // Prefer cities, then the longest name.
  const municipality = unambiguous.sort(
    (a, b) => Number(/mahanagar/i.test(b.level)) - Number(/mahanagar/i.test(a.level)) || b.name.length - a.name.length
  )[0];

  // "Kathmandu" is both a district and a city in it, and "Gandaki" both a
  // province and a rural municipality: the bigger unit wins (the district card
  // lists the city among its local governments).
  const sharesBiggerName =
    municipality &&
    (municipality.name.toLowerCase() === districtHit?.district.toLowerCase() ||
      (provinceHit && municipality.name.toLowerCase() === short(provinceHit).toLowerCase()));
  if (municipality && !sharesBiggerName) {
    const province = DISTRICT_TO_PROVINCE[municipality.district];
    return {
      kind: "municipality",
      name: municipality.name,
      province,
      district: municipality.district,
      level: getLevelLabel(municipality.level),
      mapHref: `/map?focus=${encodeURIComponent(municipality.name)}&district=${encodeURIComponent(titleCase(municipality.district))}`,
    };
  }

  if (districtHit) {
    const province = DISTRICT_TO_PROVINCE[districtHit.district];
    return {
      kind: "district",
      name: titleCase(districtHit.district),
      province,
      district: districtHit.district,
      matchedAs: districtHit.matchedAs,
      localGovernments: await localGovernmentsIn(districtHit.district),
      mapHref: `/map?focus=${encodeURIComponent(titleCase(districtHit.district))}`,
    };
  }

  const province = provinceHit;
  if (province) {
    return {
      kind: "province",
      name: province,
      province,
      districtCount: Object.values(DISTRICT_TO_PROVINCE).filter((p) => p === province).length,
      mapHref: `/map?focus=${encodeURIComponent(short(province))}`,
    };
  }

  return null;
}
