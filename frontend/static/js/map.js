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

    // Dark theme CartoDB basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
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
                    <div style="font-weight: 800; font-size: 14px; color: #f8fafc; margin-bottom: 2px;">${ins.road_name}</div>
                    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 8px;">Code: ${ins.code} | ${ins.road_type}</div>
                    
                    ${ins.annotated_url ? `<img src="${ins.annotated_url}" style="width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 8px;" />` : ''}

                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
                        <span>Risk Index:</span>
                        <span style="font-weight: 700; color: ${markerColor};">${ins.risk_score}/100 (${ins.risk_level})</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px;">
                        <span>Unique Defects:</span>
                        <span style="font-weight: 700; color: #f8fafc;">${ins.unique_defects_count} (${ins.severe_count} Severe)</span>
                    </div>

                    <button onclick="viewInspectionDetail(${ins.id})" style="width: 100%; background: #2563eb; color: #fff; border: none; padding: 6px; border-radius: 4px; font-weight: 600; font-size: 12px; cursor: pointer;">
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
