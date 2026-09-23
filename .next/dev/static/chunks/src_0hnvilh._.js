(globalThis["TURBOPACK"] || (globalThis["TURBOPACK"] = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/src/components/map/NepalMap.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "NepalMap",
    ()=>NepalMap
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$MapContainer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/MapContainer.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$TileLayer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/TileLayer.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$GeoJSON$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/GeoJSON.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$Marker$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/Marker.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$Popup$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/Popup.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/react-leaflet/lib/hooks.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/leaflet/dist/leaflet-src.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$geo$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/geo.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$map$2f$NewsPopupContent$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/components/map/NewsPopupContent.tsx [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature(), _s2 = __turbopack_context__.k.signature(), _s3 = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
const TAG_ICON = __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;border-radius:9999px;background:#2563eb;border:2px solid white;box-shadow:0 0 0 2px #2563eb55"></div>`,
    iconSize: [
        16,
        16
    ],
    iconAnchor: [
        8,
        8
    ]
});
// Nepal's approximate extent, used to fit the initial view and lock panning/zoom
// so only Nepal is ever visible (no India/China tiles around the edges). Nepal's
// bounding box is much wider than tall (~2:1); the map panel here is closer to
// square, so a strict width-fit would zoom out far enough to reveal a lot of
// India/China. MIN_ZOOM is fixed instead, trading a sliver of Nepal's easternmost/
// westernmost corners (reachable by panning, within MAX_BOUNDS) for keeping
// neighboring countries out of the default view.
const NEPAL_BOUNDS = [
    [
        26.3,
        80.0
    ],
    [
        30.5,
        88.3
    ]
];
const NEPAL_MAX_BOUNDS = [
    [
        25.9,
        79.6
    ],
    [
        30.9,
        88.7
    ]
];
const MIN_ZOOM = 8;
function BoundsController() {
    _s();
    const map = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMap"])();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "BoundsController.useEffect": ()=>{
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
                    map.fitBounds(NEPAL_BOUNDS, {
                        animate: false
                    });
                    hasFit = true;
                }
            }
            apply();
            const container = map.getContainer();
            const observer = new ResizeObserver(apply);
            observer.observe(container);
            return ({
                "BoundsController.useEffect": ()=>observer.disconnect()
            })["BoundsController.useEffect"];
        }
    }["BoundsController.useEffect"], [
        map
    ]);
    return null;
}
_s(BoundsController, "IoceErwr5KVGS9kN4RQ1bOkYMAg=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMap"]
    ];
});
_c = BoundsController;
function ClickCatcher({ onMapClick }) {
    _s1();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMapEvents"])({
        click (e) {
            onMapClick(e.latlng.lat, e.latlng.lng);
        }
    });
    return null;
}
_s1(ClickCatcher, "Ld/tk8Iz8AdZhC1l7acENaOEoCo=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMapEvents"]
    ];
});
_c1 = ClickCatcher;
function FocusHandler({ focusRequest, provinces, districts, municipalities }) {
    _s2();
    const map = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMap"])();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "FocusHandler.useEffect": ()=>{
            if (!focusRequest) return;
            if (focusRequest.kind === "province" && provinces) {
                const feature = provinces.features.find({
                    "FocusHandler.useEffect.feature": (f)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$geo$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getProvinceName"])(f).toLowerCase() === focusRequest.name.toLowerCase()
                }["FocusHandler.useEffect.feature"]);
                if (feature) {
                    map.flyToBounds(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].geoJSON(feature).getBounds(), {
                        padding: [
                            30,
                            30
                        ],
                        duration: 0.8
                    });
                }
                return;
            }
            if (focusRequest.kind === "district" && districts) {
                const feature = districts.features.find({
                    "FocusHandler.useEffect.feature": (f)=>f.properties.DISTRICT.toLowerCase() === focusRequest.name.toLowerCase()
                }["FocusHandler.useEffect.feature"]);
                if (feature) {
                    map.flyToBounds(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].geoJSON(feature).getBounds(), {
                        padding: [
                            40,
                            40
                        ],
                        duration: 0.8
                    });
                }
                return;
            }
            if (focusRequest.kind === "municipality" && municipalities) {
                const feature = municipalities.features.find({
                    "FocusHandler.useEffect.feature": (f)=>f.properties.NAME.toLowerCase() === focusRequest.name.toLowerCase() && f.properties.DISTRICT.toLowerCase() === (focusRequest.district ?? "").toLowerCase()
                }["FocusHandler.useEffect.feature"]);
                if (feature) {
                    map.flyToBounds(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].geoJSON(feature).getBounds(), {
                        padding: [
                            60,
                            60
                        ],
                        duration: 0.8
                    });
                }
            }
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }
    }["FocusHandler.useEffect"], [
        focusRequest
    ]);
    return null;
}
_s2(FocusHandler, "IoceErwr5KVGS9kN4RQ1bOkYMAg=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$hooks$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMap"]
    ];
});
_c2 = FocusHandler;
function NepalMap({ provinces, districts, municipalities, selectedProvince, onSelectProvince, selectedDistrict, onSelectDistrict, focusRequest, taggingMode, onMapClick, tags, onRemoveTag }) {
    _s3();
    const [newsTarget, setNewsTarget] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    // onEachFeature only runs once per layer, so click handlers close over stale props.
    // Read tagging mode from a ref that's always current instead of the closed-over value.
    const taggingModeRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRef"])(taggingMode);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "NepalMap.useEffect": ()=>{
            taggingModeRef.current = taggingMode;
        }
    }["NepalMap.useEffect"], [
        taggingMode
    ]);
    const filteredDistricts = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "NepalMap.useMemo[filteredDistricts]": ()=>{
            if (!districts || !selectedProvince) return null;
            return {
                ...districts,
                features: districts.features.filter({
                    "NepalMap.useMemo[filteredDistricts]": (f)=>(0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$geo$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getDistrictProvince"])(f.properties.DISTRICT) === selectedProvince
                }["NepalMap.useMemo[filteredDistricts]"])
            };
        }
    }["NepalMap.useMemo[filteredDistricts]"], [
        districts,
        selectedProvince
    ]);
    const filteredMunicipalities = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useMemo"])({
        "NepalMap.useMemo[filteredMunicipalities]": ()=>{
            if (!municipalities || !selectedDistrict) return null;
            return {
                ...municipalities,
                features: municipalities.features.filter({
                    "NepalMap.useMemo[filteredMunicipalities]": (f)=>f.properties.DISTRICT.toLowerCase() === selectedDistrict.toLowerCase()
                }["NepalMap.useMemo[filteredMunicipalities]"])
            };
        }
    }["NepalMap.useMemo[filteredMunicipalities]"], [
        municipalities,
        selectedDistrict
    ]);
    function provinceStyle(feature) {
        const name = feature ? (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$geo$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getProvinceName"])(feature) : undefined;
        const isSelected = name?.toLowerCase() === selectedProvince?.toLowerCase();
        return {
            color: isSelected ? "#1d4ed8" : "#475569",
            weight: isSelected ? 2.5 : 1.5,
            fillColor: isSelected ? "#3b82f6" : "#64748b",
            fillOpacity: isSelected ? 0.15 : 0.12
        };
    }
    function onEachProvince(feature, layer) {
        const name = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$geo$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getProvinceName"])(feature);
        layer.bindTooltip(name, {
            sticky: true,
            className: "!text-xs"
        });
        layer.on("click", ()=>{
            onSelectProvince(name);
            if (!taggingModeRef.current) {
                const center = layer.getBounds().getCenter();
                setNewsTarget({
                    name,
                    lat: center.lat,
                    lng: center.lng
                });
            }
        });
        layer.on("mouseover", ()=>layer.setStyle({
                fillOpacity: 0.3
            }));
        layer.on("mouseout", ()=>{
            const isSelected = name.toLowerCase() === selectedProvince?.toLowerCase();
            layer.setStyle({
                fillOpacity: isSelected ? 0.15 : 0.12
            });
        });
    }
    function districtStyle(feature) {
        const name = feature?.properties.DISTRICT;
        const isSelected = name?.toLowerCase() === selectedDistrict?.toLowerCase();
        return {
            color: isSelected ? "#1d4ed8" : "#64748b",
            weight: isSelected ? 2.5 : 1,
            fillColor: isSelected ? "#3b82f6" : "#94a3b8",
            fillOpacity: isSelected ? 0.25 : 0.08
        };
    }
    function onEachDistrict(feature, layer) {
        const props = feature.properties;
        layer.bindTooltip(props.DISTRICT, {
            sticky: true,
            className: "!text-xs"
        });
        layer.on("click", (e)=>{
            onSelectDistrict(props.DISTRICT);
            // In tagging mode, let the click bubble up so the map can place a tag here.
            if (taggingModeRef.current) return;
            __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].DomEvent.stopPropagation(e);
            const center = layer.getBounds().getCenter();
            setNewsTarget({
                name: props.DISTRICT,
                lat: center.lat,
                lng: center.lng
            });
        });
        layer.on("mouseover", ()=>layer.setStyle({
                fillOpacity: 0.3
            }));
        layer.on("mouseout", ()=>{
            const name = props.DISTRICT;
            const isSelected = name.toLowerCase() === selectedDistrict?.toLowerCase();
            layer.setStyle({
                fillOpacity: isSelected ? 0.25 : 0.08
            });
        });
    }
    function municipalityStyle() {
        return {
            color: "#16a34a",
            weight: 1,
            fillColor: "#22c55e",
            fillOpacity: 0.18
        };
    }
    function onEachMunicipality(feature, layer) {
        const props = feature.properties;
        layer.bindTooltip(`${props.NAME} (${props.LEVEL})`, {
            sticky: true,
            className: "!text-xs"
        });
        layer.on("click", (e)=>{
            // In tagging mode, let the click bubble up so the map can place a tag here.
            if (taggingModeRef.current) return;
            __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$leaflet$2f$dist$2f$leaflet$2d$src$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].DomEvent.stopPropagation(e);
            const center = layer.getBounds().getCenter();
            setNewsTarget({
                name: props.NAME,
                lat: center.lat,
                lng: center.lng
            });
        });
    }
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$MapContainer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["MapContainer"], {
        center: [
            28.3949,
            84.124
        ],
        zoom: MIN_ZOOM,
        minZoom: MIN_ZOOM,
        maxBounds: NEPAL_MAX_BOUNDS,
        maxBoundsViscosity: 1.0,
        className: "h-full w-full",
        style: {
            cursor: taggingMode ? "crosshair" : ""
        },
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$TileLayer$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["TileLayer"], {
                attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }, void 0, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 288,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(BoundsController, {}, void 0, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 292,
                columnNumber: 7
            }, this),
            provinces && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$GeoJSON$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["GeoJSON"], {
                data: provinces,
                style: provinceStyle,
                onEachFeature: onEachProvince
            }, `provinces-${selectedProvince ?? "none"}`, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 295,
                columnNumber: 9
            }, this),
            filteredDistricts && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$GeoJSON$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["GeoJSON"], {
                data: filteredDistricts,
                style: districtStyle,
                onEachFeature: onEachDistrict
            }, `districts-${selectedProvince}-${selectedDistrict}`, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 304,
                columnNumber: 9
            }, this),
            filteredMunicipalities && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$GeoJSON$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["GeoJSON"], {
                data: filteredMunicipalities,
                style: municipalityStyle,
                onEachFeature: onEachMunicipality
            }, `municipalities-${selectedDistrict}`, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 313,
                columnNumber: 9
            }, this),
            tags.map((tag)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$Marker$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Marker"], {
                    position: [
                        tag.lat,
                        tag.lng
                    ],
                    icon: TAG_ICON,
                    children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$Popup$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Popup"], {
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                            className: "min-w-[160px] text-sm",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "font-semibold",
                                    children: tag.label
                                }, void 0, false, {
                                    fileName: "[project]/src/components/map/NepalMap.tsx",
                                    lineNumber: 325,
                                    columnNumber: 15
                                }, this),
                                tag.note && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mt-1 text-slate-600",
                                    children: tag.note
                                }, void 0, false, {
                                    fileName: "[project]/src/components/map/NepalMap.tsx",
                                    lineNumber: 326,
                                    columnNumber: 28
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                    className: "mt-1 text-xs text-slate-400",
                                    children: [
                                        tag.lat.toFixed(4),
                                        ", ",
                                        tag.lng.toFixed(4)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/src/components/map/NepalMap.tsx",
                                    lineNumber: 327,
                                    columnNumber: 15
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                                    onClick: ()=>onRemoveTag(tag.id),
                                    className: "mt-2 text-xs font-medium text-rose-600 hover:underline",
                                    children: "Remove tag"
                                }, void 0, false, {
                                    fileName: "[project]/src/components/map/NepalMap.tsx",
                                    lineNumber: 330,
                                    columnNumber: 15
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/src/components/map/NepalMap.tsx",
                            lineNumber: 324,
                            columnNumber: 13
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/src/components/map/NepalMap.tsx",
                        lineNumber: 323,
                        columnNumber: 11
                    }, this)
                }, tag.id, false, {
                    fileName: "[project]/src/components/map/NepalMap.tsx",
                    lineNumber: 322,
                    columnNumber: 9
                }, this)),
            newsTarget && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$react$2d$leaflet$2f$lib$2f$Popup$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["Popup"], {
                position: [
                    newsTarget.lat,
                    newsTarget.lng
                ],
                eventHandlers: {
                    remove: ()=>setNewsTarget(null)
                },
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$src$2f$components$2f$map$2f$NewsPopupContent$2e$tsx__$5b$app$2d$client$5d$__$28$ecmascript$29$__["NewsPopupContent"], {
                    place: newsTarget.name
                }, void 0, false, {
                    fileName: "[project]/src/components/map/NepalMap.tsx",
                    lineNumber: 347,
                    columnNumber: 11
                }, this)
            }, `${newsTarget.name}-${newsTarget.lat}-${newsTarget.lng}`, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 342,
                columnNumber: 9
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(ClickCatcher, {
                onMapClick: onMapClick
            }, void 0, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 351,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(FocusHandler, {
                focusRequest: focusRequest,
                provinces: provinces,
                districts: districts,
                municipalities: municipalities
            }, void 0, false, {
                fileName: "[project]/src/components/map/NepalMap.tsx",
                lineNumber: 352,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/src/components/map/NepalMap.tsx",
        lineNumber: 279,
        columnNumber: 5
    }, this);
}
_s3(NepalMap, "IOuM8Z0RR6QyBetFe35IYzqTKjE=");
_c3 = NepalMap;
var _c, _c1, _c2, _c3;
__turbopack_context__.k.register(_c, "BoundsController");
__turbopack_context__.k.register(_c1, "ClickCatcher");
__turbopack_context__.k.register(_c2, "FocusHandler");
__turbopack_context__.k.register(_c3, "NepalMap");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/components/map/NepalMap.tsx [app-client] (ecmascript, next/dynamic entry)", (function(__turbopack_context__){

__turbopack_context__.n(__turbopack_context__.i("[project]/src/components/map/NepalMap.tsx [app-client] (ecmascript)"));
}),
"[project]/src/components/map/NewsPopupContent.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "NewsPopupContent",
    ()=>NewsPopupContent
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$newspaper$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Newspaper$3e$__ = __turbopack_context__.i("[project]/node_modules/lucide-react/dist/esm/icons/newspaper.mjs [app-client] (ecmascript) <export default as Newspaper>");
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$news$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/mock/news.ts [app-client] (ecmascript)");
;
;
;
function NewsPopupContent({ place }) {
    const news = (0, __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$mock$2f$news$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["generateMockNews"])(place, 4);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
        className: "w-64 max-w-[80vw]",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-900",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$newspaper$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Newspaper$3e$__["Newspaper"], {
                        className: "h-4 w-4 text-blue-600"
                    }, void 0, false, {
                        fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                        lineNumber: 10,
                        columnNumber: 9
                    }, this),
                    "Latest news · ",
                    place
                ]
            }, void 0, true, {
                fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                lineNumber: 9,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                className: "max-h-64 space-y-2 overflow-y-auto",
                children: news.map((item)=>/*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                        className: "border-b border-slate-100 pb-2 last:border-0 last:pb-0",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "text-sm font-medium leading-snug text-slate-900",
                                children: item.title
                            }, void 0, false, {
                                fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                                lineNumber: 16,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "mt-0.5 text-xs text-slate-500",
                                children: [
                                    item.source,
                                    " · ",
                                    item.publishedAt
                                ]
                            }, void 0, true, {
                                fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                                lineNumber: 17,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "mt-1 text-xs leading-relaxed text-slate-600",
                                children: item.snippet
                            }, void 0, false, {
                                fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                                lineNumber: 20,
                                columnNumber: 13
                            }, this)
                        ]
                    }, item.id, true, {
                        fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                        lineNumber: 15,
                        columnNumber: 11
                    }, this))
            }, void 0, false, {
                fileName: "[project]/src/components/map/NewsPopupContent.tsx",
                lineNumber: 13,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/src/components/map/NewsPopupContent.tsx",
        lineNumber: 8,
        columnNumber: 5
    }, this);
}
_c = NewsPopupContent;
var _c;
__turbopack_context__.k.register(_c, "NewsPopupContent");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/src/lib/mock/news.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "generateMockNews",
    ()=>generateMockNews
]);
const SOURCES = [
    "Kathmandu Post",
    "Setopati",
    "Rising Nepal",
    "PGS Wire",
    "Himal Khabar",
    "Nepal Today"
];
const HEADLINE_TEMPLATES = [
    (place)=>`${place} local unit approves new infrastructure budget for next fiscal year`,
    (place)=>`Survey team completes ward-boundary verification in ${place}`,
    (place)=>`${place} reports rise in agricultural exports this quarter`,
    (place)=>`Road expansion project in ${place} enters second phase`,
    (place)=>`${place} residents raise concerns over drinking water supply`,
    (place)=>`PGS index adds 340 new public records for ${place}`,
    (place)=>`${place} schools receive digital learning grant`,
    (place)=>`Weather advisory issued for ${place} and surrounding areas`
];
const SNIPPET_TEMPLATES = [
    (place)=>`Officials in ${place} confirmed the plan during a public hearing held earlier this week, citing community feedback as the main driver.`,
    (place)=>`The update follows a routine field survey conducted across ${place}'s wards, with results now indexed in the PGS registry.`,
    (place)=>`Local representatives say the initiative is part of a broader push to modernize public services across ${place}.`,
    (place)=>`Residents of ${place} can expect updated records to reflect these changes within the next indexing cycle.`
];
function hashString(input) {
    let hash = 0;
    for(let i = 0; i < input.length; i++){
        hash = (hash << 5) - hash + input.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash) || 1;
}
function seededRandom(seed) {
    let value = seed;
    return ()=>{
        value = (value * 9301 + 49297) % 233280;
        return value / 233280;
    };
}
const HOURS_AGO = [
    1,
    2,
    4,
    6,
    9,
    14,
    22,
    30,
    48
];
function generateMockNews(place, count = 5) {
    const rand = seededRandom(hashString(place));
    const slug = place.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
    return Array.from({
        length: count
    }).map((_, i)=>{
        const headline = HEADLINE_TEMPLATES[Math.floor(rand() * HEADLINE_TEMPLATES.length)](place);
        const snippet = SNIPPET_TEMPLATES[Math.floor(rand() * SNIPPET_TEMPLATES.length)](place);
        const hoursAgo = HOURS_AGO[Math.floor(rand() * HOURS_AGO.length)];
        return {
            id: `${slug}-news-${i}`,
            title: headline,
            source: SOURCES[Math.floor(rand() * SOURCES.length)],
            publishedAt: hoursAgo < 24 ? `${hoursAgo}h ago` : `${Math.round(hoursAgo / 24)}d ago`,
            snippet,
            url: `https://news.pgs.np/${slug}/${1000 + Math.floor(rand() * 8999)}`
        };
    });
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=src_0hnvilh._.js.map