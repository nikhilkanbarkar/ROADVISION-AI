/**
 * ROADVISION AI - Geospatial Intelligence Map (Leaflet.js)
 * Manages interactive damage pin rendering, severity color-coding, filters, and preset navigation.
 */

let roadMap = null;
let markersLayer = null;

function initRoadMap() {
    if (roadMap) return;
    const mapContainer = document.getElementById("damage-map-container");
    if (!mapContainer) return;

    // Default center: Delhi-NCR Corridor
    roadMap = L.map('damage-map-container', {
        zoomControl: true,
        attributionControl: false
    }).setView([28.5355, 77.1500], 11);

    // Crisp light theme CartoDB Voyager basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(roadMap);

    markersLayer = L.layerGroup().addTo(roadMap);
    loadMapPoints();
}

async function loadMapPoints(categoryFilter = "", severityFilter = "") {
    if (!markersLayer) return;
    markersLayer.clearLayers();

    try {
        const res = await fetch("/api/inspections?limit=100");
        const data = await res.json();
        const inspections = data.inspections || [];

        let validCount = 0;
        inspections.forEach(ins => {
            if (!ins.latitude || !ins.longitude) return;

            // Severity color
            let markerColor = "#3b82f6"; // Minor / Default Blue
            if (ins.risk_level === "Critical" || ins.severe_count > 0) {
                markerColor = "#ef4444"; // Red
            } else if (ins.risk_level === "High" || ins.moderate_count > 0) {
                markerColor = "#f59e0b"; // Orange/Amber
            } else if (ins.risk_score <= 10) {
                markerColor = "#10b981"; // Green (Repaired)
            }

            // Custom styled HTML marker pin
            const customIcon = L.divIcon({
                className: "custom-map-pin",
                html: `
                    <div style="background: ${markerColor}; width: 22px; height: 22px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 10px ${markerColor}; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 800; color: #fff;">
                        ${ins.unique_defects_count}
                    </div>
                `,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });

            const marker = L.marker([ins.latitude, ins.longitude], { icon: customIcon });

            const popupContent = `
                <div style="font-family: inherit; width: 240px; padding: 4px;">
                    <div style="font-weight: 800; font-size: 14px; color: #0f172a; margin-bottom: 2px;">${ins.road_name}</div>
                    <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">Code: ${ins.code} | ${ins.road_type}</div>
                    
                    ${ins.annotated_url ? `<img src="${ins.annotated_url}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 8px; border: 1px solid #e2e8f0;" />` : ''}

                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; color: #475569;">
                        <span>Risk Index:</span>
                        <span style="font-weight: 700; color: ${markerColor};">${ins.risk_score}/100 (${ins.risk_level})</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px; color: #475569;">
                        <span>Unique Defects:</span>
                        <span style="font-weight: 700; color: #0f172a;">${ins.unique_defects_count} (${ins.severe_count} Severe)</span>
                    </div>

                    <button onclick="viewInspectionDetail(${ins.id})" style="width: 100%; background: #2563eb; color: #fff; border: none; padding: 6px; border-radius: 6px; font-weight: 600; font-size: 12px; cursor: pointer;">
                        Inspect Report
                    </button>
                </div>
            `;

            marker.bindPopup(popupContent);
            markersLayer.addLayer(marker);
            validCount++;
        });

        console.log(`[Map] Plotted ${validCount} road inspection markers.`);
    } catch (e) {
        console.error("[Map] Failed to load map coordinates:", e);
    }
}

function flyToCorridor(lat, lon, zoom = 14) {
    if (roadMap) {
        roadMap.flyTo([lat, lon], zoom, { duration: 1.5 });
    }
}

// ==========================================
// CITIZEN COMMUTER SAFETY MAP
// ==========================================
let citizenMap = null;
let citizenMarkersLayer = null;

function initCitizenMap() {
    if (citizenMap) {
        setTimeout(() => citizenMap.invalidateSize(), 150);
        return;
    }
    const mapContainer = document.getElementById("citizen-map-container");
    if (!mapContainer) return;

    citizenMap = L.map('citizen-map-container', {
        zoomControl: true,
        attributionControl: false
    }).setView([28.5355, 77.1500], 11);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd'
    }).addTo(citizenMap);

    citizenMarkersLayer = L.layerGroup().addTo(citizenMap);
    loadCitizenMapPoints();
}

async function loadCitizenMapPoints() {
    if (!citizenMarkersLayer) return;
    citizenMarkersLayer.clearLayers();
    try {
        const res = await fetch("/api/inspections?limit=100");
        const data = await res.json();
        const inspections = data.inspections || [];

        inspections.forEach(ins => {
            if (!ins.latitude || !ins.longitude) return;

            let markerColor = "#3b82f6";
            let hazardLabel = "Minor Road Wear";
            if (ins.risk_level === "Critical" || ins.severe_count > 0) {
                markerColor = "#dc2626";
                hazardLabel = "Severe Pothole Hazard (Slow Down)";
            } else if (ins.risk_level === "High" || ins.moderate_count > 0) {
                markerColor = "#d97706";
                hazardLabel = "Moderate Road Distress";
            } else if (ins.risk_score <= 10) {
                markerColor = "#059669";
                hazardLabel = "Repaired Pavement (Safe)";
            }

            const customIcon = L.divIcon({
                className: "custom-map-pin",
                html: `
                    <div style="background: ${markerColor}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 2px 6px rgba(0,0,0,0.25); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 900; color: #fff;">
                        !
                    </div>
                `,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });

            const marker = L.marker([ins.latitude, ins.longitude], { icon: customIcon });
            const popupContent = `
                <div style="font-family: inherit; width: 240px; padding: 4px;">
                    <div style="font-weight: 800; font-size: 14px; color: #0f172a; margin-bottom: 2px;">${ins.road_name}</div>
                    <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">Reported Road Condition</div>
                    <div style="padding: 4px 8px; border-radius: 6px; background: #f8fafc; border: 1px solid #e2e8f0; font-size: 11px; font-weight: 700; color: ${markerColor}; margin-bottom: 8px;">
                        ${hazardLabel}
                    </div>
                    ${ins.annotated_url ? `<img src="${ins.annotated_url}" style="width: 100%; height: 105px; object-fit: cover; border-radius: 6px; margin-bottom: 6px; border: 1px solid #e2e8f0;" />` : ''}
                    <div style="font-size: 11px; color: #475569;">
                        Status: <strong>${ins.risk_score <= 10 ? 'Repaired & Verified' : 'Under Municipal Action'}</strong>
                    </div>
                </div>
            `;
            marker.bindPopup(popupContent);
            citizenMarkersLayer.addLayer(marker);
        });
    } catch(e) {
        console.error("Citizen map error:", e);
    }
}
