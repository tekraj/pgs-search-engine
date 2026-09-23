"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap, useMapEvents } from "react-leaflet";
import L, { type Layer, type LeafletMouseEvent } from "leaflet";
import type { Feature } from "geojson";
import {
  getDistrictProvince,
  getProvinceName,
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

// Nepal's approximate extent, used to fit the initial view and lock panning/zoom
// so only Nepal is ever visible (no India/China tiles around the edges). Nepal's
// bounding box is much wider than tall (~2:1); the map panel here is closer to
// square, so a strict width-fit would zoom out far enough to reveal a lot of
// India/China. MIN_ZOOM is fixed instead, trading a sliver of Nepal's easternmost/
// westernmost corners (reachable by panning, within MAX_BOUNDS) for keeping
// neighboring countries out of the default view.
const NEPAL_BOUNDS: L.LatLngBoundsExpression = [
  [26.3, 80.0],
  [30.5, 88.3],
];
const NEPAL_MAX_BOUNDS: L.LatLngBoundsExpression = [
  [25.9, 79.6],
  [30.9, 88.7],
];
const MIN_ZOOM = 8;

export interface FocusRequest {
  seq: number;
  kind: "province" | "district" | "municipality";
  name: string;
  district?: string;
}

function BoundsController() {
  const map = useMap();

  useEffect(() => {
    let hasFit = false;

    function apply() {
      // Inside a flex layout the container can report a 0/stale size on the very
      // first tick; invalidateSize() forces Leaflet to re-measure before we fit.
      map.invalidateSize();

      // Only snap to the full-Nepal view once, the first time we see a real
      // container size — later resizes (sidebar toggling, window resize) must
      // not undo the user's own pan/zoom.
      const size = map.getSize();
      if (!hasFit && size.x > 0 && size.y > 0) {
        map.fitBounds(NEPAL_BOUNDS, { animate: false });
        hasFit = true;
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

function ClickCatcher({ onMapClick }: { onMapClick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e: LeafletMouseEvent) {
      onMapClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
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
  onSelectProvince,
  selectedDistrict,
  onSelectDistrict,
  focusRequest,
  taggingMode,
  onMapClick,
  tags,
  onRemoveTag,
}: {
  provinces: ProvinceCollection | null;
  districts: DistrictCollection | null;
  municipalities: MunicipalityCollection | null;
  selectedProvince: string | null;
  onSelectProvince: (name: string) => void;
  selectedDistrict: string | null;
  onSelectDistrict: (name: string) => void;
  focusRequest: FocusRequest | null;
  taggingMode: boolean;
  onMapClick: (lat: number, lng: number) => void;
  tags: GeoTag[];
  onRemoveTag: (id: string) => void;
}) {
  const [newsTarget, setNewsTarget] = useState<{ name: string; lat: number; lng: number } | null>(null);

  // onEachFeature only runs once per layer, so click handlers close over stale props.
  // Read tagging mode from a ref that's always current instead of the closed-over value.
  const taggingModeRef = useRef(taggingMode);
  useEffect(() => {
    taggingModeRef.current = taggingMode;
  }, [taggingMode]);

  const filteredDistricts = useMemo(() => {
    if (!districts || !selectedProvince) return null;
    return {
      ...districts,
      features: districts.features.filter(
        (f) => getDistrictProvince(f.properties.DISTRICT) === selectedProvince
      ),
    };
  }, [districts, selectedProvince]);

  const filteredMunicipalities = useMemo(() => {
    if (!municipalities || !selectedDistrict) return null;
    return {
      ...municipalities,
      features: municipalities.features.filter(
        (f) => f.properties.DISTRICT.toLowerCase() === selectedDistrict.toLowerCase()
      ),
    };
  }, [municipalities, selectedDistrict]);

  function provinceStyle(feature?: Feature) {
    const name = feature ? getProvinceName(feature as ProvinceFeature) : undefined;
    const isSelected = name?.toLowerCase() === selectedProvince?.toLowerCase();
    return {
      color: isSelected ? "#1d4ed8" : "#475569",
      weight: isSelected ? 2.5 : 1.5,
      fillColor: isSelected ? "#3b82f6" : "#64748b",
      fillOpacity: isSelected ? 0.15 : 0.12,
    };
  }

  function onEachProvince(feature: Feature, layer: Layer) {
    const name = getProvinceName(feature as ProvinceFeature);
    layer.bindTooltip(name, { sticky: true, className: "!text-xs" });
    layer.on("click", () => {
      onSelectProvince(name);
      if (!taggingModeRef.current) {
        const center = (layer as L.Polygon).getBounds().getCenter();
        setNewsTarget({ name, lat: center.lat, lng: center.lng });
      }
    });
    layer.on("mouseover", () => (layer as L.Path).setStyle({ fillOpacity: 0.3 }));
    layer.on("mouseout", () => {
      const isSelected = name.toLowerCase() === selectedProvince?.toLowerCase();
      (layer as L.Path).setStyle({ fillOpacity: isSelected ? 0.15 : 0.12 });
    });
  }

  function districtStyle(feature?: Feature) {
    const name = (feature as DistrictFeature | undefined)?.properties.DISTRICT;
    const isSelected = name?.toLowerCase() === selectedDistrict?.toLowerCase();
    return {
      color: isSelected ? "#1d4ed8" : "#64748b",
      weight: isSelected ? 2.5 : 1,
      fillColor: isSelected ? "#3b82f6" : "#94a3b8",
      fillOpacity: isSelected ? 0.25 : 0.08,
    };
  }

  function onEachDistrict(feature: Feature, layer: Layer) {
    const props = (feature as DistrictFeature).properties;
    layer.bindTooltip(props.DISTRICT, { sticky: true, className: "!text-xs" });
    layer.on("click", (e: LeafletMouseEvent) => {
      onSelectDistrict(props.DISTRICT);
      // In tagging mode, let the click bubble up so the map can place a tag here.
      if (taggingModeRef.current) return;
      L.DomEvent.stopPropagation(e);
      const center = (layer as L.Polygon).getBounds().getCenter();
      setNewsTarget({ name: props.DISTRICT, lat: center.lat, lng: center.lng });
    });
    layer.on("mouseover", () => (layer as L.Path).setStyle({ fillOpacity: 0.3 }));
    layer.on("mouseout", () => {
      const name = props.DISTRICT;
      const isSelected = name.toLowerCase() === selectedDistrict?.toLowerCase();
      (layer as L.Path).setStyle({ fillOpacity: isSelected ? 0.25 : 0.08 });
    });
  }

  function municipalityStyle() {
    return {
      color: "#16a34a",
      weight: 1,
      fillColor: "#22c55e",
      fillOpacity: 0.18,
    };
  }

  function onEachMunicipality(feature: Feature, layer: Layer) {
    const props = (feature as MunicipalityFeature).properties;
    layer.bindTooltip(`${props.NAME} (${props.LEVEL})`, { sticky: true, className: "!text-xs" });
    layer.on("click", (e: LeafletMouseEvent) => {
      // In tagging mode, let the click bubble up so the map can place a tag here.
      if (taggingModeRef.current) return;
      L.DomEvent.stopPropagation(e);
      const center = (layer as L.Polygon).getBounds().getCenter();
      setNewsTarget({ name: props.NAME, lat: center.lat, lng: center.lng });
    });
  }

  return (
    <MapContainer
      center={[28.3949, 84.124]}
      zoom={MIN_ZOOM}
      minZoom={MIN_ZOOM}
      maxBounds={NEPAL_MAX_BOUNDS}
      maxBoundsViscosity={1.0}
      className="h-full w-full"
      style={{ cursor: taggingMode ? "crosshair" : "" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <BoundsController />

      {provinces && (
        <GeoJSON
          key={`provinces-${selectedProvince ?? "none"}`}
          data={provinces}
          style={provinceStyle}
          onEachFeature={onEachProvince}
        />
      )}

      {filteredDistricts && (
        <GeoJSON
          key={`districts-${selectedProvince}-${selectedDistrict}`}
          data={filteredDistricts}
          style={districtStyle}
          onEachFeature={onEachDistrict}
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
              <p className="mt-1 text-xs text-slate-400">
                {tag.lat.toFixed(4)}, {tag.lng.toFixed(4)}
              </p>
              <button
                onClick={() => onRemoveTag(tag.id)}
                className="mt-2 text-xs font-medium text-rose-600 hover:underline"
              >
                Remove tag
              </button>
            </div>
          </Popup>
        </Marker>
      ))}

      {newsTarget && (
        <Popup
          key={`${newsTarget.name}-${newsTarget.lat}-${newsTarget.lng}`}
          position={[newsTarget.lat, newsTarget.lng]}
          eventHandlers={{ remove: () => setNewsTarget(null) }}
        >
          <NewsPopupContent place={newsTarget.name} />
        </Popup>
      )}

      <ClickCatcher onMapClick={onMapClick} />
      <FocusHandler
        focusRequest={focusRequest}
        provinces={provinces}
        districts={districts}
        municipalities={municipalities}
      />
    </MapContainer>
  );
}
