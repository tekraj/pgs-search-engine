// Number and time formatting for the dashboard. Fixed locale and Nepal time,
// so the server and the browser always print the same text.

const integer = new Intl.NumberFormat("en-US");
const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 });

/** 12450 → "12,450" */
export function formatNumber(value: number): string {
  return integer.format(value);
}

/** 14250000 → "14.25M" */
export function formatCompact(value: number): string {
  return compact.format(value);
}

/** Part of a whole as a whole-number percent, never NaN. */
export function percent(part: number, whole: number): number {
  return whole > 0 ? Math.round((part / whole) * 100) : 0;
}

// Nepal is UTC+5:45 all year (no daylight saving). Formatting by hand instead
// of with Intl keeps the text identical in Node and every browser.
const NPT_OFFSET_MS = (5 * 60 + 45) * 60_000;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function nepalTime(iso: string) {
  const d = new Date(new Date(iso).getTime() + NPT_OFFSET_MS);
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    day: d.getUTCDate(),
    month: MONTHS[d.getUTCMonth()],
    year: d.getUTCFullYear(),
    hh: pad(d.getUTCHours()),
    mm: pad(d.getUTCMinutes()),
    ss: pad(d.getUTCSeconds()),
  };
}

/** "14:05" in Nepal time. */
export function formatClock(iso: string, withSeconds = false): string {
  const t = nepalTime(iso);
  return withSeconds ? `${t.hh}:${t.mm}:${t.ss}` : `${t.hh}:${t.mm}`;
}

/** "16 Sep 2026, 14:05 NPT", for tooltips. */
export function formatFullDate(iso: string): string {
  const t = nepalTime(iso);
  return `${t.day} ${t.month} ${t.year}, ${t.hh}:${t.mm} NPT`;
}

/** "just now", "5 min ago", "3 h ago", "2 days ago". */
export function timeAgo(iso: string, now: number): string {
  const minutes = Math.max(0, Math.round((now - new Date(iso).getTime()) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
