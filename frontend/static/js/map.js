/**
 * RoadGuard AI - Geospatial Intelligence Map (Leaflet.js)
 * Primary Geographical Scope: Belagavi, Karnataka, India
 * Manages 3-tier color-coded road conditions (RED: Risky, YELLOW: Moderate, GREEN: Safe),
 * Belagavi boundary rendering, verified pothole pins, and risk-aware multi-route rendering.
 */

let roadMap = null;
let roadSegmentsLayer = null;
let markersLayer = null;
let routeLayersGroup = null;
let boundaryLayer = null;

// Belagavi City Center Coordinates
const BELAGAVI_CENTER = [15.8497, 74.4977];
const BELAGAVI_BOUNDS_COORDS = [
    [15.8950, 74.4600],
    [15.9250, 74.5200],
    [15.8900, 74.5700],
    [15.8200, 74.5700],
    [15.8050, 74.5450],
    [15.8050, 74.4800],
    [15.8450, 74.4550],
    [15.8950, 74.4600]
];

function createMapTileLayer() {
    const savedKey = localStorage.getItem("roadvision_map_key") || "";
    if (savedKey) {
        return L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=${savedKey}`, {
            maxZoom: 19,
            subdomains: 'abcd',
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        });
    }

    // Default: 100% Free OpenStreetMap Tiles (NO API key required)
    return L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        subdomains: 'abc',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });
}

function initRoadMap() {
    if (roadMap) {
        setTimeout(() => roadMap.invalidateSize(), 150);
        return;
    }
    const mapContainer = document.getElementById("damage-map-container");
    if (!mapContainer) return;

    // Center on Belagavi City, Karnataka
    roadMap = L.map('damage-map-container', {
        zoomControl: true
    }).setView(BELAGAVI_CENTER, 13);

    createMapTileLayer().addTo(roadMap);

    // Belagavi Municipal Boundary Overlay
    boundaryLayer = L.polygon(BELAGAVI_BOUNDS_COORDS, {
        color: "#2563eb",
        weight: 2,
        dashArray: "6, 6",
        fillColor: "#3b82f6",
        fillOpacity: 0.04
    }).addTo(roadMap);
    boundaryLayer.bindTooltip("Belagavi City Corporation Limits", { sticky: true });

    roadSegmentsLayer = L.layerGroup().addTo(roadMap);
    markersLayer = L.layerGroup().addTo(roadMap);
    routeLayersGroup = L.layerGroup().addTo(roadMap);

    loadMapPoints();

    // Map click handler to pick GPS coordinates
    roadMap.on("click", (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lon = e.latlng.lng.toFixed(5);
        const citizenCoordsInput = document.getElementById("citizen-coords");
        if (citizenCoordsInput) {
            citizenCoordsInput.value = `${lat}, ${lon}`;
        }
    });
}

async function loadMapPoints(riskFilter = "") {
    if (!roadMap) initRoadMap();
    if (!roadSegmentsLayer || !markersLayer) return;

    roadSegmentsLayer.clearLayers();
    markersLayer.clearLayers();

    try {
        // 1. Fetch official road condition records from database
        const res = await fetch("/api/roads/condition");
        const data = await res.json();
        const roads = data.roads || [];

        let riskyCount = 0;
        let moderateCount = 0;
        let safeCount = 0;

        roads.forEach(road => {
            const riskClass = (road.risk_classification || "SAFE").toUpperCase();
            if (riskFilter && riskFilter.toUpperCase() !== riskClass) return;

            if (riskClass === "RISKY") riskyCount++;
            else if (riskClass === "MODERATE") moderateCount++;
            else safeCount++;

            // 3-Tier Classification Colors:
            // RISKY / CRITICAL: RED (#ef4444)
            // MODERATE: YELLOW / AMBER (#f59e0b)
            // SAFE: GREEN (#10b981)
            let color = "#10b981"; // Safe Green
            let weight = 5;
            let opacity = 0.85;

            if (riskClass === "RISKY") {
                color = "#ef4444"; // Red
                weight = 6;
                opacity = 0.95;
            } else if (riskClass === "MODERATE") {
                color = "#f59e0b"; // Yellow / Amber
                weight = 5;
                opacity = 0.85;
            }

            // Convert coordinates from [lon, lat] to Leaflet [lat, lon]
            if (road.coordinates && road.coordinates.length > 0) {
                const latLngs = road.coordinates.map(pt => [pt[1], pt[0]]);
                const polyline = L.polyline(latLngs, {
                    color: color,
                    weight: weight,
                    opacity: opacity,
                    lineJoin: "round",
                    lineCap: "round"
                }).addTo(roadSegmentsLayer);

                // Build rich popup
                const popupContent = createRoadPopupHTML(road, color);
                polyline.bindPopup(popupContent);

                // Also place a marker pin if there are detected potholes
                if (road.potholes_count > 0 && road.mid_lat && road.mid_lon) {
                    const pinIcon = L.divIcon({
                        className: "road-pothole-pin",
                        html: `
                            <div style="background: ${color}; color: #ffffff; border: 2px solid #ffffff; width: 22px; height: 22px; border-radius: 50%; box-shadow: 0 0 8px ${color}; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 900;">
                                ${road.potholes_count}
                            </div>
                        `,
                        iconSize: [22, 22],
                        iconAnchor: [11, 11]
                    });

                    const pinMarker = L.marker([road.mid_lat, road.mid_lon], { icon: pinIcon });
                    pinMarker.bindPopup(popupContent);
                    markersLayer.addLayer(pinMarker);
                }
            }
        });

        // 2. Also load granular verified physical damage records (defects)
        try {
            const defRes = await fetch("/api/physical-damage?limit=50");
            const defData = await defRes.json();
            const defects = defData.physical_defects || [];

            defects.forEach(d => {
                if (!d.latitude || !d.longitude) return;

                let markerColor = "#3b82f6";
                if (d.severity === "Severe" || d.risk_score >= 70) {
                    markerColor = "#ef4444";
                } else if (d.severity === "Moderate" || d.risk_score >= 40) {
                    markerColor = "#f59e0b";
                } else if (d.repair_status === "Repaired" || d.risk_score <= 15) {
                    markerColor = "#10b981";
                }

                const customIcon = L.divIcon({
                    className: "custom-map-pin",
                    html: `
                        <div style="background: ${markerColor}; width: 18px; height: 18px; border-radius: 50%; border: 2px solid #ffffff; box-shadow: 0 0 6px ${markerColor}; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800; color: #fff;">
                            !
                        </div>
                    `,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                const m = L.marker([d.latitude, d.longitude], { icon: customIcon });
                m.bindPopup(`
                    <div style="font-family: inherit; width: 230px; padding: 2px;">
                        <div style="font-weight: 800; font-size: 13px; color: #0f172a;">${d.road_name}</div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">Defect Code: <strong>${d.damage_code}</strong></div>
                        <div style="font-size: 11px; margin-bottom: 2px;">Severity: <strong style="color: ${markerColor};">${d.severity}</strong></div>
                        <div style="font-size: 11px; margin-bottom: 2px;">Risk Score: <strong>${d.risk_score}/100</strong></div>
                        <div style="font-size: 10px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px; margin-top: 4px;">
                            Status: <strong>${d.repair_status || 'Under Municipal Action'}</strong>
                        </div>
                    </div>
                `);
                markersLayer.addLayer(m);
            });
        } catch(err) {
            console.warn("Defects load error:", err);
        }

        console.log(`[Belagavi GIS Map] Rendered road network (${roads.length} corridors). Filter: ${riskFilter || 'All'}`);
    } catch (e) {
        console.error("[Belagavi Map] Failed to load road conditions:", e);
    }
}

function createRoadPopupHTML(road, color) {
    const riskBadgeText = road.risk_classification === "RISKY" ? "CRITICAL / RISKY" : (road.risk_classification === "MODERATE" ? "MODERATE" : "SAFE");
    const osmNames = Array.isArray(road.osm_names) ? road.osm_names.filter(Boolean).join(" / ") : "";
    return `
        <div style="font-family: inherit; width: 260px; padding: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                <span style="font-size: 10px; font-weight: 900; text-transform: uppercase; padding: 2px 8px; border-radius: 9999px; background: ${color}20; color: ${color}; border: 1px solid ${color}40;">
                    ${riskBadgeText}
                </span>
                <span style="font-size: 11px; font-weight: 700; color: #64748b;">${road.road_type || 'Road'} &bull; ${road.speed_limit || 60} km/h</span>
            </div>
            <div style="font-weight: 800; font-size: 14px; color: #0f172a; margin-bottom: 2px; line-height: 1.25;">${road.name}</div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">Location: <strong>${road.location || 'Belagavi'}</strong></div>
            ${osmNames ? `<div style="font-size: 10px; color: #64748b; margin-bottom: 6px;">OSM street names: <strong>${osmNames}</strong></div>` : ""}

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                    <span style="color: #475569; font-weight: 600;">Road Condition:</span>
                    <strong style="color: ${color}; font-size: 13px;">${road.condition_percentage}%</strong>
                </div>
                <div style="width: 100%; height: 6px; background: #e2e8f0; border-radius: 9999px; overflow: hidden; margin-bottom: 6px;">
                    <div style="width: ${road.condition_percentage}%; height: 100%; background: ${color}; border-radius: 9999px;"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #475569;">
                    <span>Detected Potholes:</span>
                    <strong style="color: ${road.potholes_count > 0 ? '#ef4444' : '#10b981'}; font-size: 12px;">${road.potholes_count}</strong>
                </div>
            </div>

            <div style="font-size: 10px; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 4px; display: flex; justify-content: space-between;">
                <span>Last Inspected: <strong>${road.last_inspected_date || 'Recent'}</strong></span>
                <span>Source: <strong>${road.inspection_source || 'Official'}</strong></span>
            </div>
            <div style="font-size: 9px; color: #64748b; margin-top: 4px;">Geometry: ${road.geometry_source || "OSRM/OpenStreetMap"} · &copy; OpenStreetMap contributors</div>
        </div>
    `;
}

function filterRoadMap(riskFilter) {
    loadMapPoints(riskFilter);
}

function flyToCorridor(lat, lon, zoom = 14) {
    if (roadMap) {
        roadMap.flyTo([lat, lon], zoom, { duration: 1.5 });
    }
}

// ==========================================
// CITIZEN COMMUTER ROAD SAFETY MAP
// ==========================================
let citizenMap = null;
let citizenRoadsLayer = null;
let citizenMarkersLayer = null;
let citizenRouteGroup = null;

function initCitizenMap() {
    if (citizenMap) {
        setTimeout(() => citizenMap.invalidateSize(), 150);
        return;
    }
    const mapContainer = document.getElementById("citizen-map-container");
    if (!mapContainer) return;

    citizenMap = L.map('citizen-map-container', {
        zoomControl: true
    }).setView(BELAGAVI_CENTER, 13);

    createMapTileLayer().addTo(citizenMap);

    // Belagavi Boundary
    L.polygon(BELAGAVI_BOUNDS_COORDS, {
        color: "#059669",
        weight: 2,
        dashArray: "6, 6",
        fillColor: "#10b981",
        fillOpacity: 0.04
    }).addTo(citizenMap);

    citizenRoadsLayer = L.layerGroup().addTo(citizenMap);
    citizenMarkersLayer = L.layerGroup().addTo(citizenMap);
    citizenRouteGroup = L.layerGroup().addTo(citizenMap);

    loadCitizenMapPoints();

    // Map click handler to pick GPS coordinates
    citizenMap.on("click", (e) => {
        const lat = e.latlng.lat.toFixed(5);
        const lon = e.latlng.lng.toFixed(5);
        const citizenCoordsInput = document.getElementById("citizen-coords");
        if (citizenCoordsInput) {
            citizenCoordsInput.value = `${lat}, ${lon}`;
        }
    });
}

async function loadCitizenMapPoints(riskFilter = "") {
    if (!citizenMap) initCitizenMap();
    if (!citizenRoadsLayer || !citizenMarkersLayer) return;

    citizenRoadsLayer.clearLayers();
    citizenMarkersLayer.clearLayers();

    try {
        const res = await fetch("/api/roads/condition");
        const data = await res.json();
        const roads = data.roads || [];

        roads.forEach(road => {
            const riskClass = (road.risk_classification || "SAFE").toUpperCase();
            if (riskFilter && riskFilter.toUpperCase() !== riskClass) return;

            let color = "#10b981";
            let weight = 5;
            let opacity = 0.85;

            if (riskClass === "RISKY") {
                color = "#ef4444";
                weight = 6;
                opacity = 0.95;
            } else if (riskClass === "MODERATE") {
                color = "#f59e0b";
                weight = 5;
                opacity = 0.85;
            }

            if (road.coordinates && road.coordinates.length > 0) {
                const latLngs = road.coordinates.map(pt => [pt[1], pt[0]]);
                const polyline = L.polyline(latLngs, {
                    color: color,
                    weight: weight,
                    opacity: opacity,
                    lineJoin: "round",
                    lineCap: "round"
                }).addTo(citizenRoadsLayer);

                const popupContent = createRoadPopupHTML(road, color);
                polyline.bindPopup(popupContent);

                if (road.potholes_count > 0 && road.mid_lat && road.mid_lon) {
                    const pinIcon = L.divIcon({
                        className: "road-pothole-pin",
                        html: `
                            <div style="background: ${color}; color: #ffffff; border: 2px solid #ffffff; width: 22px; height: 22px; border-radius: 50%; box-shadow: 0 0 8px ${color}; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 900;">
                                ${road.potholes_count}
                            </div>
                        `,
                        iconSize: [22, 22],
                        iconAnchor: [11, 11]
                    });

                    const pinMarker = L.marker([road.mid_lat, road.mid_lon], { icon: pinIcon });
                    pinMarker.bindPopup(popupContent);
                    citizenMarkersLayer.addLayer(pinMarker);
                }
            }
        });
    } catch(e) {
        console.error("Citizen map error:", e);
    }
}

// ==========================================
// ROUTE RECOMMENDATION RENDERING
// ==========================================
function renderRoutesOnMap(routeResponse, targetMap = "citizen") {
    const map = (targetMap === "authority" && roadMap) ? roadMap : (citizenMap || roadMap);
    const layerGroup = (targetMap === "authority" && routeLayersGroup) ? routeLayersGroup : (citizenRouteGroup || routeLayersGroup);

    if (!map || !layerGroup) return;
    layerGroup.clearLayers();

    if (!routeResponse || !routeResponse.routes || routeResponse.routes.length === 0) return;

    const routes = routeResponse.routes;
    const recId = routeResponse.recommended_route_id;
    const bounds = [];
    const displayRoutes = [
        ...routes.filter(route => route.route_id !== recId),
        ...routes.filter(route => route.route_id === recId)
    ];

    displayRoutes.forEach(r => {
        const isRecommended = (r.route_id === recId);
        const polylineCoords = r.polyline || [];
        if (polylineCoords.length === 0) return;

        polylineCoords.forEach(c => bounds.push(c));

        const risk = String(r.risk_level || "").toLowerCase();
        const color = r.risk_color || r.color || (
            risk === "critical" || risk === "high" ? "#dc2626" :
                risk === "moderate" ? "#d97706" : "#059669"
        );
        const weight = isRecommended ? 8 : 5;
        const opacity = isRecommended ? 0.98 : 0.82;

        const line = L.polyline(polylineCoords, {
            color: color,
            weight: weight,
            opacity: opacity,
            lineJoin: "round",
            lineCap: "round"
        }).addTo(layerGroup);

        const popup = `
            <div style="padding: 4px; font-family: inherit; width: 240px;">
                <div style="font-weight: 900; font-size: 13px; color: ${color}; margin-bottom: 4px;">
                    ${isRecommended ? '⭐ RECOMMENDED ROUTE' : `ALTERNATIVE ROUTE ${r.route_id}`} · ${r.risk_level || 'Unknown'} risk
                </div>
                <div style="font-size: 12px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">${r.name}</div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span>Distance:</span>
                    <strong>${r.distance_km} km</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span>Estimated Time:</span>
                    <strong>${r.estimated_time_min} mins</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span>Distress Exposure:</span>
                    <strong style="color: ${r.risk_color || color};">${r.exposure_score} / 100 (${r.risk_level})</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
                    <span>Distance / risk score:</span>
                    <strong>${r.recommendation_score}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
                    <span>Potholes on Route:</span>
                    <strong style="color: ${r.potholes_count > 0 ? '#dc2626' : '#059669'};">${r.potholes_count}</strong>
                </div>
                <div style="font-size: 10px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 4px;">
                    ${r.factors && r.factors[0] ? r.factors[0] : 'Evaluated against official verified road condition database'}
                </div>
            </div>
        `;
        line.bindPopup(popup);

        if (isRecommended) {
            line.openPopup();
        }
    });

    if (routeResponse.origin) {
        const startIcon = L.divIcon({
            className: "nav-start-pin",
            html: `<div style="background: #10b981; color: #fff; width: 24px; height: 24px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900;">A</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });
        const mStart = L.marker([routeResponse.origin.lat, routeResponse.origin.lon], { icon: startIcon });
        mStart.bindPopup(`<b>Start Origin:</b><br>${routeResponse.origin.junction || 'Origin Point'}`);
        layerGroup.addLayer(mStart);
    }

    if (routeResponse.destination) {
        const endIcon = L.divIcon({
            className: "nav-end-pin",
            html: `<div style="background: #2563eb; color: #fff; width: 24px; height: 24px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900;">B</div>`,
            iconSize: [26, 26],
            iconAnchor: [13, 13]
        });
        const mEnd = L.marker([routeResponse.destination.lat, routeResponse.destination.lon], { icon: endIcon });
        mEnd.bindPopup(`<b>Destination:</b><br>${routeResponse.destination.junction || 'Destination Point'}`);
        layerGroup.addLayer(mEnd);
    }

    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [40, 40] });
    }
}
