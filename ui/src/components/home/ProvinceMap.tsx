import fs from "node:fs/promises";
import path from "node:path";
import type { Position } from "geojson";
import { PROVINCE_NAMES, getProvinceColor, type ProvinceCollection } from "@/lib/geo";

// A lightweight, clickable map of Nepal's seven provinces for the home page.
// It's rendered on the server straight from public/data, so it ships as plain
// SVG — no Leaflet, no client JavaScript, and no extra request.

const WIDTH = 800;
// Stretch latitude so the country keeps roughly the proportions it has on the
// full map (Mercator at ~28°N).
const LAT_STRETCH = 1.13;

interface ProvinceShape {
  name: string;
  shortName: string;
  color: string;
  d: string;
  labelX: number;
  labelY: number;
}

let cached: Promise<{ shapes: ProvinceShape[]; height: number }> | null = null;

function loadShapes() {
  cached ??= (async () => {
    const file = path.join(process.cwd(), "public", "data", "nepal-provinces.geojson");
    const data = JSON.parse(await fs.readFile(file, "utf8")) as ProvinceCollection;

    const rings = (geometry: ProvinceCollection["features"][number]["geometry"]): Position[][] =>
      geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates.flat();

    let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity;
    for (const feature of data.features) {
      for (const ring of rings(feature.geometry)) {
        for (const [lng, lat] of ring) {
          minLng = Math.min(minLng, lng);
          maxLng = Math.max(maxLng, lng);
          minLat = Math.min(minLat, lat);
          maxLat = Math.max(maxLat, lat);
        }
      }
    }
    const scale = WIDTH / (maxLng - minLng);
    const project = ([lng, lat]: Position): [number, number] => [
      (lng - minLng) * scale,
      (maxLat - lat) * scale * LAT_STRETCH,
    ];

    const shapes = data.features.map((feature) => {
      const name = PROVINCE_NAMES[feature.properties.ADM1_PCODE] ?? feature.properties.ADM1_EN;
      let d = "";
      // Area-weighted centroid of all rings, for the label.
      let area = 0, cx = 0, cy = 0;
      for (const ring of rings(feature.geometry)) {
        let lastX = NaN, lastY = NaN;
        const points: [number, number][] = [];
        for (const position of ring) {
          const [x, y] = project(position);
          // Points closer than ~1px add bytes but no visible detail at this size.
          if (Math.abs(x - lastX) < 1 && Math.abs(y - lastY) < 1) continue;
          points.push([x, y]);
          lastX = x;
          lastY = y;
        }
        if (points.length < 3) continue;
        d += `M${points.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L")}Z`;
        for (let i = 0; i < points.length; i++) {
          const [x0, y0] = points[i];
          const [x1, y1] = points[(i + 1) % points.length];
          const cross = x0 * y1 - x1 * y0;
          area += cross;
          cx += (x0 + x1) * cross;
          cy += (y0 + y1) * cross;
        }
      }
      return {
        name,
        shortName: name.replace(" Province", ""),
        color: getProvinceColor(name),
        d,
        labelX: cx / (3 * area),
        labelY: cy / (3 * area),
      };
    });

    return { shapes, height: (maxLat - minLat) * scale * LAT_STRETCH };
  })();
  return cached;
}

export async function ProvinceMap() {
  const { shapes, height } = await loadShapes();

  return (
    <svg
      viewBox={`-4 -4 ${WIDTH + 8} ${height + 8}`}
      className="h-auto w-full"
      role="group"
      aria-label="Map of Nepal's seven provinces. Choose a province to explore it on the map."
    >
      {shapes.map((shape) => (
        <a
          key={shape.name}
          href={`/map?focus=${encodeURIComponent(shape.shortName)}`}
          aria-label={`${shape.name}: open on the map`}
          className="group outline-none"
        >
          <title>{`${shape.name} — open on the map`}</title>
          <path
            d={shape.d}
            fill={shape.color}
            stroke="#ffffff"
            strokeWidth={2}
            strokeLinejoin="round"
            className="cursor-pointer transition-[filter] duration-150 group-hover:brightness-90 group-focus-visible:brightness-90 group-focus-visible:[stroke:#1d4ed8] group-focus-visible:[stroke-width:4]"
          />
          <text
            x={shape.labelX}
            y={shape.labelY}
            textAnchor="middle"
            dominantBaseline="middle"
            className="pointer-events-none select-none fill-slate-900 text-[15px] font-semibold"
            style={{ paintOrder: "stroke", stroke: "#ffffff", strokeWidth: 3, strokeLinejoin: "round" }}
          >
            {shape.shortName}
          </text>
        </a>
      ))}
    </svg>
  );
}
