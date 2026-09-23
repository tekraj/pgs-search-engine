"use client";

import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Popup } from "react-leaflet";
import L, { type Layer } from "leaflet";
import type { Feature } from "geojson";
import "leaflet/dist/leaflet.css";
import { NewsPopupContent } from "@/components/map/NewsPopupContent";
import type { DistrictFeature, DistrictCollection, MunicipalityCollection, MunicipalityFeature } from "@/lib/geo";

const NEPAL_CENTER: [number, number] = [28.3949, 84.124];

interface NewsTarget {
  name: string;
  lat: number;
  lng: number;
}

export function DemoNewsMapView() {
  const [districts, setDistricts] = useState<DistrictCollection | null>(null);
  const [municipalities, setMunicipalities] = useState<MunicipalityCollection | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<string | null>(null);
  const [newsTarget, setNewsTarget] = useState<NewsTarget | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/nepal-districts.geojson").then((r) => r.json()),
      fetch("/data/nepal-municipalities.geojson").then((r) => r.json()),
    ]).then(([d, m]: [DistrictCollection, MunicipalityCollection]) => {
      setDistricts(d);
      setMunicipalities({
        ...m,
        features: m.features.filter((f) => f.properties.NAME && f.properties.N_ID),
      });
    });
  }, []);

  const filteredMunicipalities = useMemo(() => {
    if (!municipalities || !selectedDistrict) return null;
    return {
      ...municipalities,
      features: municipalities.features.filter(
        (f) => f.properties.DISTRICT.toLowerCase() === selectedDistrict.toLowerCase()
      ),
    };
  }, [municipalities, selectedDistrict]);

  function districtStyle(feature?: Feature) {
    const name = (feature as DistrictFeature | undefined)?.properties.DISTRICT;
    const isSelected = name?.toLowerCase() === selectedDistrict?.toLowerCase();
    return {
      color: isSelected ? "#1d4ed8" : "#64748b",
      weight: isSelected ? 2.5 : 1,
      fillColor: isSelected ? "#3b82f6" : "#94a3b8",
      fillOpacity: isSelected ? 0.2 : 0.08,
    };
  }

  function onEachDistrict(feature: Feature, layer: Layer) {
    const props = (feature as DistrictFeature).properties;
    layer.bindTooltip(props.DISTRICT, { sticky: true, className: "!text-xs" });
    layer.on("click", () => {
      const center = (layer as L.Polygon).getBounds().getCenter();
      setSelectedDistrict(props.DISTRICT);
      setNewsTarget({ name: props.DISTRICT, lat: center.lat, lng: center.lng });
    });
  }

  function municipalityStyle() {
    return { color: "#16a34a", weight: 1, fillColor: "#22c55e", fillOpacity: 0.18 };
  }

  function onEachMunicipality(feature: Feature, layer: Layer) {
    const props = (feature as MunicipalityFeature).properties;
    layer.bindTooltip(`${props.NAME} (${props.LEVEL})`, { sticky: true, className: "!text-xs" });
    layer.on("click", (e) => {
      L.DomEvent.stopPropagation(e);
      const center = (layer as L.Polygon).getBounds().getCenter();
      setNewsTarget({ name: props.NAME, lat: center.lat, lng: center.lng });
    });
  }

  return (
    <div className="flex h-full w-full flex-col">
      <div className="border-b border-slate-200 bg-blue-50 px-4 py-2 text-sm text-blue-800 dark:border-slate-800 dark:bg-blue-500/10 dark:text-blue-300">
        Demo: click any district (or, once selected, a municipality) to pop up its latest news.
      </div>
      <div className="relative flex-1">
        <MapContainer center={NEPAL_CENTER} zoom={7} minZoom={6} className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {districts && (
            <GeoJSON data={districts} style={districtStyle} onEachFeature={onEachDistrict} />
          )}

          {filteredMunicipalities && (
            <GeoJSON
              key={selectedDistrict}
              data={filteredMunicipalities}
              style={municipalityStyle}
              onEachFeature={onEachMunicipality}
            />
          )}

          {newsTarget && (
            <Popup
              key={`${newsTarget.name}-${newsTarget.lat}-${newsTarget.lng}`}
              position={[newsTarget.lat, newsTarget.lng]}
              eventHandlers={{ remove: () => setNewsTarget(null) }}
            >
              <NewsPopupContent place={newsTarget.name} />
            </Popup>
          )}
        </MapContainer>
      </div>
    </div>
  );
}
