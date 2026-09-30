"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, GeoJSON, Marker, Popup, useMap, useMapEvents } from "react-leaflet";
import L, { type Layer, type LeafletMouseEvent, type PathOptions } from "leaflet";
import type { Feature } from "geojson";
import { House, Minus, MousePointerClick, Plus } from "lucide-react";
import {
  getDistrictProvince,
  getLevelLabel,
  getProvinceColor,
  getProvinceName,
  titleCase,
  type DistrictFeature,
  type DistrictCollection,
  type MunicipalityCollection,
  type MunicipalityFeature,
  type ProvinceCollection,
  type ProvinceFeature,
} from "@/lib/geo";
import type { GeoTag } from "@/lib/types";
import { NewsPopupContent } from "@/components/map/NewsPopupContent";

const TAG_ICON = L.divIcon({
  className: "",
  html: `<div style="width:16px;height:16px;border-radius:9999px;background:#2563eb;border:2px solid white;box-shadow:0 0 0 2px #2563eb55"></div>`,
  iconSize: [16, 16],
  iconAnchor: [8, 8],
});

// The spot the user just clicked in pin mode, before they've named it.
const PENDING_ICON = L.divIcon({
  className: "",
  html: `<div style="width:18px;height:18px;border-radius:9999px;background:#f59e0b;border:3px solid white;box-shadow:0 0 0 3px #f59e0b66"></div>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

// Nepal's approximate extent, used to fit the initial view. There's no tile
// basemap to worry about bleeding into India/China anymore (the GeoJSON is
// drawn on a blank canvas), so the view is free to zoom out as far as it
// needs to fit Nepal's full ~2:1 width. That full-country fit is also the
// zoom-out limit — past it there's only blank canvas.
const NEPAL_BOUNDS = L.latLngBounds([26.3, 80.0], [30.5, 88.3]);
const NEPAL_MAX_BOUNDS: L.LatLngBoundsExpression = [
  [25.9, 79.6],
  [30.9, 88.7],
];
// Floor low enough that fitBounds can always show the whole country regardless
// of panel aspect ratio; ceiling generous enough for the municipality-level
// flyTo when focusing a search result.
const MIN_ZOOM = 5;
const MAX_ZOOM = 13;

export interface FocusRequest {
  seq: number;
  kind: "country" | "province" | "district" | "municipality";
  name: string;
  district?: string;
}

function BoundsController() {
  const map = useMap();

  useEffect(() => {
    function apply() {
      // Inside a flex layout the container can report a 0/stale, pre-layout size
      // on early ticks; invalidateSize() forces Leaflet to re-measure before we
      // fit. Re-fitting on every resize (sidebar toggle, window resize) keeps the
      // full country filling the panel instead of freezing at whatever size the
      // container happened to be first; it does reset any zoom the user applied.
      map.invalidateSize();

      const size = map.getSize();
      if (size.x > 0 && size.y > 0) {
        // Drop the floor first: a smaller panel needs a lower fit zoom than the
        // previous floor, and fitBounds would otherwise clamp to it and clip.
        map.setMinZoom(MIN_ZOOM);
        map.fitBounds(NEPAL_BOUNDS, { animate: false, padding: [8, 8] });
        map.setMinZoom(map.getZoom());
      }
    }

    apply();
    const container = map.getContainer();
    const observer = new ResizeObserver(apply);
    observer.observe(container);
    return () => observer.disconnect();
  }, [map]);

  return null;
}

// At the full-country view there's nothing to pan to, so dragging only turns on
// once the user has zoomed in (via buttons, wheel/pinch, or a focus flyTo).
// Zooming back out from an off-center spot would otherwise land at the min zoom
// slightly shifted, clipping one edge of the country — so recenter there.
function PanWhenZoomed() {
  const map = useMap();
  useMapEvents({
    zoomend() {
      if (map.getZoom() > map.getMinZoom() + 0.01) {
        map.dragging.enable();
        return;
      }
      map.dragging.disable();
      // Popups belong to the zoomed-in context and won't fit the full-country
      // box without clipping.
      map.closePopup();
      // fitBounds centers on the projected (Mercator) midpoint, not the lat/lng
      // one, so compare in pixel space to match the initial full-country view.
      const zoom = map.getZoom();
      const target = map
        .project(NEPAL_BOUNDS.getSouthWest(), zoom)
        .add(map.project(NEPAL_BOUNDS.getNorthEast(), zoom))
        .divideBy(2);
      if (map.project(map.getCenter(), zoom).distanceTo(target) > 1) {
        map.panTo(map.unproject(target, zoom));
      }
    },
  });
  return null;
}

// Rendered as a sibling overlay rather than inside the Leaflet container: clicks
// then never reach Leaflet's own handlers (district select, tagging), and we
// avoid L.DomEvent.disableClickPropagation, which would also swallow the native
// event before React's root listener sees it.
function ZoomControls({ map }: { map: L.Map }) {
  const [zoomState, setZoomState] = useState(() => ({
    zoom: map.getZoom(),
    min: map.getMinZoom(),
    max: map.getMaxZoom(),
  }));

  useEffect(() => {
    // The min zoom moves whenever the panel resizes (see BoundsController), so
    // re-read it alongside the zoom itself.
    function sync() {
      setZoomState({ zoom: map.getZoom(), min: map.getMinZoom(), max: map.getMaxZoom() });
    }
    sync();
    map.on("zoomend zoomlevelschange resize", sync);
    return () => {
      map.off("zoomend zoomlevelschange resize", sync);
    };
  }, [map]);

  const atMin = zoomState.zoom <= zoomState.min + 0.01;
  const atMax = zoomState.zoom >= zoomState.max - 0.01;
  const buttonClass =
    "flex h-8 w-8 items-center justify-center text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-300 disabled:hover:bg-transparent";

  return (
    <div className="absolute right-3 top-3 z-[1000] flex flex-col divide-y divide-slate-200 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
      <button type="button" aria-label="Zoom in" title="Zoom in" disabled={atMax} onClick={() => map.zoomIn(1)} className={buttonClass}>
        <Plus className="h-4 w-4" />
      </button>
      <button type="button" aria-label="Zoom out" title="Zoom out" disabled={atMin} onClick={() => map.zoomOut(1)} className={buttonClass}>
        <Minus className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-label="Show all of Nepal"
        title="Show all of Nepal"
        disabled={atMin}
        onClick={() => map.flyToBounds(NEPAL_BOUNDS, { padding: [8, 8], duration: 0.6 })}
        className={buttonClass}
      >
        <House className="h-4 w-4" />
      </button>
    </div>
  );
}


function FocusHandler({
  focusRequest,
  provinces,
  districts,
  municipalities,
}: {
  focusRequest: FocusRequest | null;
  provinces: ProvinceCollection | null;
  districts: DistrictCollection | null;
  municipalities: MunicipalityCollection | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!focusRequest) return;

    if (focusRequest.kind === "country") {
      map.flyToBounds(NEPAL_BOUNDS, { padding: [8, 8], duration: 0.8 });
      return;
    }

    if (focusRequest.kind === "province" && provinces) {
      const feature = provinces.features.find(
        (f) => getProvinceName(f).toLowerCase() === focusRequest.name.toLowerCase()
      );
      if (feature) {
        map.flyToBounds(L.geoJSON(feature).getBounds(), { padding: [30, 30], duration: 0.8 });
      }
      return;
    }

    if (focusRequest.kind === "district" && districts) {
      const feature = districts.features.find(
        (f) => f.properties.DISTRICT.toLowerCase() === focusRequest.name.toLowerCase()
      );
      if (feature) {
        map.flyToBounds(L.geoJSON(feature).getBounds(), { padding: [40, 40], duration: 0.8 });
      }
      return;
    }

    if (focusRequest.kind === "municipality" && municipalities) {
      const feature = municipalities.features.find(
        (f) =>
          f.properties.NAME.toLowerCase() === focusRequest.name.toLowerCase() &&
          f.properties.DISTRICT.toLowerCase() === (focusRequest.district ?? "").toLowerCase()
      );
      if (feature) {
        map.flyToBounds(L.geoJSON(feature).getBounds(), { padding: [60, 60], duration: 0.8 });
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusRequest]);

  return null;
}

export function NepalMap({
  provinces,
  districts,
  municipalities,
  selectedProvince,
  selectedDistrict,
  onSelectDistrict,
  focusRequest,
  taggingMode,
  onMapClick,
  pendingTag,
  tags,
  onRemoveTag,
}: {
  provinces: ProvinceCollection | null;
  districts: DistrictCollection | null;
  municipalities: MunicipalityCollection | null;
  selectedProvince: string | null;
  // Districts now cover the whole map, so selecting one (which also implies its
  // province, handled in GeoExplorer) covers what a province-only click used to
  // do. Kept in the prop contract since GeoExplorer still passes it through.
  onSelectProvince: (name: string) => void;
  selectedDistrict: string | null;
  onSelectDistrict: (name: string) => void;
  focusRequest: FocusRequest | null;
  taggingMode: boolean;
  onMapClick: (lat: number, lng: number, district?: string) => void;
  pendingTag: { lat: number; lng: number } | null;
  tags: GeoTag[];
  onRemoveTag: (id: string) => void;
}) {
  const [newsTarget, setNewsTarget] = useState<{ name: string; lat: number; lng: number } | null>(null);
  const [map, setMap] = useState<L.Map | null>(null);
  const [hoveredDistrict, setHoveredDistrict] = useState<string | null>(null);
  const districtLayersRef = useRef(new Map<string, L.Polygon>());

  // At the full-country view small districts (Kathmandu valley, the Madhesh
  // strip) are only a few pixels wide and their names pile into each other.
  // Hide any label that doesn't fit its own district; zooming in reveals it,
  // and the hover card still names every district.
  const updateLabelVisibility = useCallback(() => {
    if (!map) return;
    districtLayersRef.current.forEach((layer, name) => {
      const el = layer.getTooltip()?.getElement();
      if (!el || !map.hasLayer(layer)) return;
      const bounds = layer.getBounds();
      const nw = map.latLngToContainerPoint(bounds.getNorthWest());
      const se = map.latLngToContainerPoint(bounds.getSouthEast());
      const labelWidth = titleCase(name).length * 6;
      const fits = se.x - nw.x >= labelWidth && se.y - nw.y >= 16;
      const isSelected = name.toLowerCase() === selectedDistrict?.toLowerCase();
      el.classList.toggle("district-label--hidden", !fits && !isSelected);
    });
  }, [map, selectedDistrict]);

  useEffect(() => {
    if (!map) return;
    updateLabelVisibility();
    map.on("zoomend", updateLabelVisibility);
    return () => {
      map.off("zoomend", updateLabelVisibility);
    };
  }, [map, updateLabelVisibility, districts, selectedProvince]);

  // onEachFeature only runs once per layer, so click handlers close over stale props.
  // Read tagging mode from a ref that's always current instead of the closed-over value.
  const taggingModeRef = useRef(taggingMode);
  const onMapClickRef = useRef(onMapClick);
  useEffect(() => {
    taggingModeRef.current = taggingMode;
    onMapClickRef.current = onMapClick;
  }, [taggingMode, onMapClick]);

  const filteredMunicipalities = useMemo(() => {
    if (!municipalities || !selectedDistrict) return null;
    return {
      ...municipalities,
      features: municipalities.features.filter(
        (f) => f.properties.DISTRICT.toLowerCase() === selectedDistrict.toLowerCase()
      ),
    };
  }, [municipalities, selectedDistrict]);

  // Every district renders at once, tinted by its province, like a printed
  // administrative map — selection just dims everything outside the active
  // province and picks out the active district's border.
  function districtStyle(feature?: Feature): PathOptions {
    const name = (feature as DistrictFeature | undefined)?.properties.DISTRICT ?? "";
    const province = getDistrictProvince(name);
    const isSelectedDistrict = name.toLowerCase() === selectedDistrict?.toLowerCase();
    const isHovered = name === hoveredDistrict;
    const isDimmed = Boolean(selectedProvince) && province !== selectedProvince;

    return {
      color: isSelectedDistrict ? "#1d4ed8" : isHovered ? "#0f172a" : "#ffffff",
      weight: isSelectedDistrict || isHovered ? 2.5 : 1,
      fillColor: getProvinceColor(province),
      fillOpacity: isDimmed ? (isHovered ? 0.45 : 0.2) : isSelectedDistrict || isHovered ? 1 : 0.82,
    };
  }

  function onEachDistrict(feature: Feature, layer: Layer) {
    const props = (feature as DistrictFeature).properties;
    districtLayersRef.current.set(props.DISTRICT, layer as L.Polygon);
    layer.bindTooltip(titleCase(props.DISTRICT), {
      permanent: true,
      direction: "center",
      className: "district-label",
      interactive: false,
    });
    layer.on("click", (e: LeafletMouseEvent) => {
      L.DomEvent.stopPropagation(e);
      // Pin mode: drop the pin where they clicked, without selecting the district
      // (selecting would fly the map away from the spot they just picked).
      if (taggingModeRef.current) {
        onMapClickRef.current(e.latlng.lat, e.latlng.lng, props.DISTRICT);
        return;
      }
      onSelectDistrict(props.DISTRICT);
      const center = (layer as L.Polygon).getBounds().getCenter();
      setNewsTarget({ name: props.DISTRICT, lat: center.lat, lng: center.lng });
    });
    // Hover styling lives in districtStyle: GeoJSON re-applies `style` on every
    // render, which would wipe a setStyle() made here.
    layer.on("mouseover", () => setHoveredDistrict(props.DISTRICT));
    layer.on("mouseout", () => setHoveredDistrict((current) => (current === props.DISTRICT ? null : current)));
  }

  // Province outlines sit on top purely as a bolder boundary between
  // same-colored district clusters — no fill, no clicks of their own (the
  // district layer beneath already reports province selection on click).
  function provinceBoundaryStyle(feature?: Feature): PathOptions {
    const name = feature ? getProvinceName(feature as ProvinceFeature) : undefined;
    const isSelected = name?.toLowerCase() === selectedProvince?.toLowerCase();
    return {
      fill: false,
      color: isSelected ? "#1d4ed8" : "#334155",
      weight: isSelected ? 3 : 1.75,
      opacity: isSelected ? 1 : 0.75,
      interactive: false,
    };
  }

  function municipalityStyle(): PathOptions {
    return {
      color: "#16a34a",
      weight: 1,
      fillColor: "#22c55e",
      fillOpacity: 0.18,
    };
  }

  function onEachMunicipality(feature: Feature, layer: Layer) {
    const props = (feature as MunicipalityFeature).properties;
    layer.bindTooltip(`${props.NAME} · ${getLevelLabel(props.LEVEL)}`, { sticky: true, className: "!text-xs" });
    layer.on("click", (e: LeafletMouseEvent) => {
      L.DomEvent.stopPropagation(e);
      if (taggingModeRef.current) {
        onMapClickRef.current(e.latlng.lat, e.latlng.lng, props.DISTRICT);
        return;
      }
      const center = (layer as L.Polygon).getBounds().getCenter();
      setNewsTarget({ name: props.NAME, lat: center.lat, lng: center.lng });
    });
  }

  return (
    // NEPAL_BOUNDS is ~1.73:1 in Leaflet's Mercator projection; a stretched
    // full-height panel just letterboxes it in white space. Size the Leaflet box
    // to just over that ratio and fitBounds then fills it nearly edge to edge.
    <div className="flex h-full w-full items-center justify-center p-2 sm:p-4">
      <div
        // Phones fill the panel instead: the country is width-bound either way,
        // and the extra card height gives news popups room to open.
        className={`relative h-full w-full overflow-hidden rounded-xl border bg-white shadow-sm sm:aspect-[7/4] sm:h-auto sm:max-h-full ${
          taggingMode
            ? "border-amber-400 ring-2 ring-amber-300/60 [&_.leaflet-container]:!cursor-crosshair [&_.leaflet-interactive]:!cursor-crosshair"
            : "border-slate-200 dark:border-slate-700"
        }`}
      >
      <MapContainer
        ref={setMap}
        center={[28.3949, 84.124]}
        zoom={MIN_ZOOM}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        // Whole-number zoom snapping makes fitBounds round down to the next level
        // that fits, which can leave the country at roughly half the panel size.
        zoomSnap={0}
        maxBounds={NEPAL_MAX_BOUNDS}
        maxBoundsViscosity={1.0}
        zoomControl={false}
        dragging={false}
        scrollWheelZoom
        touchZoom
        doubleClickZoom={false}
        boxZoom={false}
        keyboard={false}
        attributionControl={false}
        className="h-full w-full bg-white"
      >
        <BoundsController />
        <PanWhenZoomed />

        {districts && (
          <GeoJSON
            key={`districts-${selectedProvince ?? "none"}-${selectedDistrict ?? "none"}`}
            data={districts}
            style={districtStyle}
            onEachFeature={onEachDistrict}
          />
        )}

        {provinces && (
          <GeoJSON
            key={`province-outline-${selectedProvince ?? "none"}`}
            data={provinces}
            style={provinceBoundaryStyle}
          />
        )}

        {filteredMunicipalities && (
          <GeoJSON
            key={`municipalities-${selectedDistrict}`}
            data={filteredMunicipalities}
            style={municipalityStyle}
            onEachFeature={onEachMunicipality}
          />
        )}

        {tags.map((tag) => (
          <Marker key={tag.id} position={[tag.lat, tag.lng]} icon={TAG_ICON}>
            <Popup>
              <div className="min-w-[160px] text-sm">
                <p className="font-semibold">{tag.label}</p>
                {tag.note && <p className="mt-1 text-slate-600">{tag.note}</p>}
                {tag.district && (
                  <p className="mt-1 text-xs text-slate-500">{titleCase(tag.district)} district</p>
                )}
                <button
                  type="button"
                  onClick={() => onRemoveTag(tag.id)}
                  className="mt-2 text-xs font-medium text-rose-600 hover:underline"
                >
                  Delete pin
                </button>
              </div>
            </Popup>
          </Marker>
        ))}

        {pendingTag && (
          <Marker position={[pendingTag.lat, pendingTag.lng]} icon={PENDING_ICON} interactive={false} />
        )}

        {newsTarget && (
          <Popup
            key={`${newsTarget.name}-${newsTarget.lat}-${newsTarget.lng}`}
            position={[newsTarget.lat, newsTarget.lng]}
            eventHandlers={{ remove: () => setNewsTarget(null) }}
          >
            {/* The popup opens while a flyTo recenters the clicked place, which
                overrides Leaflet's autoPan — so cap the list to the space above
                center (minus header, padding and tip). */}
            <NewsPopupContent
              place={titleCase(newsTarget.name)}
              listMaxHeight={map ? Math.max(90, map.getSize().y / 2 - 110) : undefined}
            />
          </Popup>
        )}

        <FocusHandler
          focusRequest={focusRequest}
          provinces={provinces}
          districts={districts}
          municipalities={municipalities}
        />
      </MapContainer>
      {map && <ZoomControls map={map} />}
      {hoveredDistrict && <HoverCard district={hoveredDistrict} taggingMode={taggingMode} />}
      </div>

      <style jsx global>{`
        .leaflet-container {
          background: #ffffff !important;
        }

        .district-label {
          background: transparent;
          border: none;
          box-shadow: none;
          padding: 0;
          margin: 0;
          font-size: 10px;
          font-weight: 600;
          line-height: 1;
          color: #0f172a;
          text-shadow:
            -1px -1px 0 #fff,
            1px -1px 0 #fff,
            -1px 1px 0 #fff,
            1px 1px 0 #fff,
            0 0 3px #fff;
          pointer-events: none;
          white-space: nowrap;
        }

        .district-label--hidden {
          visibility: hidden;
        }
      `}</style>
    </div>
  );
}

// Names the district under the pointer (even when its map label is hidden for
// space), shows which province it belongs to, and says what a click will do.
// Tucked in the bottom-left corner, which Nepal's shape leaves empty. Hidden on
// touch screens: a tap fires mouseover but never mouseout, so it would stick.
function HoverCard({ district, taggingMode }: { district: string; taggingMode: boolean }) {
  const province = getDistrictProvince(district);
  return (
    <div className="pointer-events-none absolute bottom-3 left-3 z-[1000] hidden max-w-[70%] rounded-lg border border-slate-200 bg-white/95 px-3 py-2 shadow-md [@media(hover:hover)]:block">
      <p className="text-sm font-semibold text-slate-900">{titleCase(district)} district</p>
      {province && (
        <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-600">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: getProvinceColor(province) }} />
          {province}
        </p>
      )}
      <p className="mt-1 flex items-center gap-1 text-xs font-medium text-blue-700">
        <MousePointerClick className="h-3.5 w-3.5" />
        {taggingMode ? "Click to drop your pin here" : "Click to see local news"}
      </p>
    </div>
  );
}
