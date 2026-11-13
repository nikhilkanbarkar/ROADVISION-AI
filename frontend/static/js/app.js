/**
 * ROADVISION AI - Central Application Controller
 * Handles tab navigation, asynchronous API integration, dashboard analytics,
 * image/video inspections, duplicate resolution, repair lifecycle, and reporting.
 */

let categoryChart = null;
let severityChart = null;
let activeInspectionId = null;

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    loadDashboardAnalytics();
    setupDropzone();
    setupVideoDropzone();
});

// ==========================================
// 1. NAVIGATION & TAB SWITCHING
// ==========================================
function initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const targetTab = item.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".nav-item").forEach(el => {
        el.classList.remove("bg-blue-600/20", "text-blue-400", "border-l-4", "border-blue-500");
        el.classList.add("text-slate-400");
    });

    const activeNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    if (activeNav) {
        activeNav.classList.add("bg-blue-600/20", "text-blue-400", "border-l-4", "border-blue-500");
        activeNav.classList.remove("text-slate-400");
    }

    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    const targetContent = document.getElementById(`tab-${tabId}`);
    if (targetContent) {
        targetContent.classList.add("active");
    }

    // Lazy load tab specific components
    if (tabId === "map") {
        setTimeout(initRoadMap, 200);
    } else if (tabId === "history") {
        loadInspectionHistory();
    } else if (tabId === "duplicates") {
        loadDuplicates();
    } else if (tabId === "repairs") {
        loadRepairs();
    } else if (tabId === "verification") {
        loadUnverifiedDefects();
    } else if (tabId === "benchmark") {
        loadBenchmarkMetrics();
    } else if (tabId === "overview") {
        loadDashboardAnalytics();
    }
}

// ==========================================
// 2. DASHBOARD & ANALYTICS
// ==========================================
async function loadDashboardAnalytics() {
    try {
        const res = await fetch("/api/analytics");
        const data = await res.json();
        const kpis = data.kpis;

        // Populate KPI Cards
        document.getElementById("kpi-total-inspections").textContent = kpis.total_inspections;
        document.getElementById("kpi-total-defects").textContent = kpis.total_defects;
        document.getElementById("kpi-unique-potholes").textContent = kpis.unique_potholes;
        document.getElementById("kpi-severe-damage").textContent = kpis.severe_damage;
        document.getElementById("kpi-critical-locations").textContent = kpis.critical_risk_locations;
        document.getElementById("kpi-repairs-active").textContent = kpis.repairs_in_progress;
        document.getElementById("kpi-repairs-verified").textContent = kpis.verified_repairs;

        // Render Category Doughnut Chart
        renderCategoryChart(data.category_distribution);

        // Render Severity Bar Chart
        renderSeverityChart(data.severity_distribution);

        // Populate Recent Surveys Table
        renderRecentSurveys(data.recent_inspections);
    } catch (e) {
        console.error("[Dashboard] Error fetching analytics:", e);
    }
}

function renderCategoryChart(catData) {
    const ctx = document.getElementById("chart-categories");
    if (!ctx) return;
    if (categoryChart) categoryChart.destroy();

    categoryChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Longitudinal (D00)', 'Transverse (D10)', 'Alligator (D20)', 'Pothole (D40)'],
            datasets: [{
                data: [catData.D00 || 0, catData.D10 || 0, catData.D20 || 0, catData.D40 || 0],
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12 } }
            },
            cutout: '68%'
        }
    });
}

function renderSeverityChart(sevData) {
    const ctx = document.getElementById("chart-severities");
    if (!ctx) return;
    if (severityChart) severityChart.destroy();

    severityChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Minor Distress', 'Moderate Hazard', 'Severe / Critical'],
            datasets: [{
                label: 'Defect Count',
                data: [sevData.Minor || 0, sevData.Moderate || 0, sevData.Severe || 0],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });
}

function renderRecentSurveys(recentList) {
    const tbody = document.getElementById("recent-surveys-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!recentList || recentList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-500">No surveys recorded yet.</td></tr>`;
        return;
    }

    recentList.forEach(item => {
        let riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400">Low</span>`;
        if (item.risk_level === "Moderate") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400">Moderate</span>`;
        if (item.risk_level === "High") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-orange-500/20 text-orange-400">High</span>`;
        if (item.risk_level === "Critical") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400 pulse-glow-critical">Critical</span>`;

        const row = document.createElement("tr");
        row.className = "border-b border-slate-800 hover:bg-slate-800/40 transition";
        row.innerHTML = `
            <td class="py-3 px-4 font-mono text-xs text-blue-400">${item.code}</td>
            <td class="py-3 px-4 font-medium text-slate-200">${item.road_name}</td>
            <td class="py-3 px-4 text-xs uppercase text-slate-400">${item.media_type}</td>
            <td class="py-3 px-4 text-sm font-semibold">${item.unique_defects}</td>
            <td class="py-3 px-4">${riskBadge}</td>
            <td class="py-3 px-4 text-right">
                <button onclick="viewInspectionDetail(${item.id})" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded border border-slate-700">
                    Inspect
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// 3. IMAGE INSPECTION PIPELINE
// ==========================================
function setupDropzone() {
    const dropzone = document.getElementById("image-dropzone");
    const fileInput = document.getElementById("image-file-input");
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dropzone-active");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dropzone-active"));
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dropzone-active");
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleImageSelected(fileInput.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleImageSelected(fileInput.files[0]);
        }
    });
}

function handleImageSelected(file) {
    const preview = document.getElementById("image-preview");
    const placeholder = document.getElementById("dropzone-placeholder");
    const reader = new FileReader();

    reader.onload = (e) => {
        preview.src = e.target.result;
        preview.classList.remove("hidden");
        placeholder.classList.add("hidden");
    };
    reader.readAsDataURL(file);
}

async function runImageInspection() {
    const fileInput = document.getElementById("image-file-input");
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select or drop a road image to inspect.");
        return;
    }

    const btn = document.getElementById("btn-run-image-inspect");
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">&#9696;</span> AI Analyzing Road Defects...`;

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("road_name", document.getElementById("img-road-name").value || "Ring Road Expressway");
    formData.append("road_type", document.getElementById("img-road-type").value || "Arterial");
    formData.append("speed_limit", document.getElementById("img-speed-limit").value || "60");
    formData.append("weather", document.getElementById("img-weather").value || "Clear/Dry");
    formData.append("traffic", document.getElementById("img-traffic").value || "Moderate");
    formData.append("conf_thresh", document.getElementById("img-conf-thresh").value || "0.20");

    try {
        const res = await fetch("/api/inspect/image", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (data.status === "success") {
            displayImageInspectionResults(data);
        } else {
            alert("Inspection error: " + (data.detail || "Unknown error"));
        }
    } catch (e) {
        console.error(e);
        alert("Failed to execute inspection. See console.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `Start AI Damage Detection`;
    }
}

function displayImageInspectionResults(data) {
    document.getElementById("img-results-panel").classList.remove("hidden");
    document.getElementById("img-annotated-result").src = data.annotated_url;

    // Set Risk Meter
    const score = data.risk_score;
    document.getElementById("img-risk-score").textContent = score;
    document.getElementById("img-risk-level").textContent = data.risk_level.toUpperCase();

    const meterBar = document.getElementById("img-risk-bar");
    meterBar.style.width = `${score}%`;
    meterBar.className = "h-full transition-all duration-500 rounded-full " + (
        score <= 25 ? "bg-emerald-500" : (score <= 50 ? "bg-amber-500" : (score <= 75 ? "bg-orange-500" : "bg-rose-500"))
    );

    // Populate Defect Table
    const tbody = document.getElementById("img-defects-table-body");
    tbody.innerHTML = "";

    if (data.defects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-slate-500">No defects detected. Road pavement is in sound condition.</td></tr>`;
    } else {
        data.defects.forEach(d => {
            let sevColor = d.severity === "Minor" ? "text-emerald-400" : (d.severity === "Moderate" ? "text-amber-400" : "text-rose-400");
            const row = document.createElement("tr");
            row.className = "border-b border-slate-800 text-xs";
            row.innerHTML = `
                <td class="py-2.5 px-3 font-mono text-blue-400">${d.track_id}</td>
                <td class="py-2.5 px-3 font-medium text-slate-200">${d.display_name} (${d.category_code})</td>
                <td class="py-2.5 px-3 font-semibold ${sevColor}">${d.severity}</td>
                <td class="py-2.5 px-3">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-2.5 px-3">${(d.relative_area * 100).toFixed(2)}%</td>
            `;
            tbody.appendChild(row);
        });
    }

    // Duplicate alert banner
    const dupAlert = document.getElementById("img-duplicate-alert");
    if (data.duplicate_warnings && data.duplicate_warnings.length > 0) {
        dupAlert.classList.remove("hidden");
        document.getElementById("img-dup-text").textContent = `Notice: ${data.duplicate_warnings.length} possible duplicate defect(s) detected near this location.`;
    } else {
        dupAlert.classList.add("hidden");
    }

    // Store active inspection for export
    activeInspectionId = data.inspection_id;
}

// ==========================================
// 4. VIDEO INSPECTION & MULTI-OBJECT TRACKING
// ==========================================
function setupVideoDropzone() {
    const dropzone = document.getElementById("video-dropzone");
    const fileInput = document.getElementById("video-file-input");
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", (e) => {
        // Prevent re-triggering file picker if clicking video preview controls
        if (e.target.tagName.toLowerCase() === "video") return;
        fileInput.click();
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("border-cyan-400", "bg-cyan-950/20");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("border-cyan-400", "bg-cyan-950/20");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-cyan-400", "bg-cyan-950/20");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleVideoSelected(fileInput.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleVideoSelected(fileInput.files[0]);
        }
    });
}

function handleVideoSelected(file) {
    if (!file) return;

    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const selectedInfo = document.getElementById("video-selected-info");
    const selectedName = document.getElementById("video-selected-name");
    const selectedMeta = document.getElementById("video-selected-meta");
    const videoPreview = document.getElementById("video-input-preview");
    const btnText = document.getElementById("btn-run-video-text");

    if (selectedName) selectedName.textContent = file.name;
    if (selectedMeta) {
        selectedMeta.textContent = `Size: ${sizeMB} MB | Format: ${file.type || file.name.split('.').pop().toUpperCase()} | Status: Ready for AI analysis`;
    }
    if (selectedInfo) selectedInfo.classList.remove("hidden");

    if (btnText) {
        btnText.textContent = `Process & Track Video (${sizeMB} MB)`;
    }

    if (videoPreview) {
        try {
            const url = URL.createObjectURL(file);
            videoPreview.src = url;
            videoPreview.classList.remove("hidden");
            videoPreview.load();
        } catch (e) {
            console.warn("Could not preview video directly:", e);
        }
    }

    if (window.lucide) lucide.createIcons();
}

async function runVideoInspection() {
    const fileInput = document.getElementById("video-file-input");
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select or drop a road survey video file (.mp4, .avi, .mov, etc.) first.");
        return;
    }

    const file = fileInput.files[0];
    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    const btn = document.getElementById("btn-run-video-inspect");
    const progressContainer = document.getElementById("video-progress-container");
    const progressText = document.getElementById("video-progress-text");
    const progressSub = document.getElementById("video-progress-sub");

    btn.disabled = true;
    progressContainer.classList.remove("hidden");
    if (progressText) progressText.textContent = `Uploading & analyzing video (${sizeMB} MB)...`;
    if (progressSub) progressSub.textContent = "AI Processing";

    const strideSelect = document.getElementById("vid-stride");
    const strideVal = strideSelect ? strideSelect.value : (file.size > 8 * 1024 * 1024 ? "3" : "2");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("road_name", document.getElementById("vid-road-name").value || "Outer Ring Roadway");
    formData.append("road_type", document.getElementById("vid-road-type").value || "Highway");
    formData.append("speed_limit", document.getElementById("vid-speed-limit").value || "80");
    formData.append("weather", document.getElementById("vid-weather").value || "Clear/Dry");
    formData.append("conf_thresh", document.getElementById("vid-conf-thresh").value || "0.15");
    formData.append("stride", strideVal);

    try {
        const res = await fetch("/api/inspect/video", {
            method: "POST",
            body: formData
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server responded with HTTP ${res.status}`);
        }

        const data = await res.json();

        if (data.status === "success") {
            displayVideoInspectionResults(data);
        } else {
            alert("Video processing warning: " + (data.detail || "Unknown error occurred"));
        }
    } catch (e) {
        console.error("Video inspection error:", e);
        alert(`Video processing failed: ${e.message}\n\nPlease verify the video format and retry.`);
    } finally {
        btn.disabled = false;
        progressContainer.classList.add("hidden");
        const btnText = document.getElementById("btn-run-video-text");
        if (btnText) btnText.textContent = `Process & Track Video (${sizeMB} MB)`;
    }
}

function displayVideoInspectionResults(data) {
    document.getElementById("video-results-panel").classList.remove("hidden");
    const videoPlayer = document.getElementById("video-player");
    videoPlayer.src = data.annotated_video_url;
    videoPlayer.load();

    document.getElementById("vid-total-detections").textContent = data.total_frame_detections;
    document.getElementById("vid-unique-defects").textContent = data.unique_defects_count;
    document.getElementById("vid-risk-score").textContent = data.risk_score;

    const tbody = document.getElementById("video-tracks-table-body");
    tbody.innerHTML = "";

    data.tracked_defects.forEach(tr => {
        let sevColor = tr.severity === "Minor" ? "text-emerald-400" : (tr.severity === "Moderate" ? "text-amber-400" : "text-rose-400");
        const row = document.createElement("tr");
        row.className = "border-b border-slate-800 text-xs";
        row.innerHTML = `
            <td class="py-2.5 px-3 font-mono font-bold text-cyan-400">${tr.track_id}</td>
            <td class="py-2.5 px-3 font-medium text-slate-200">${tr.display_name}</td>
            <td class="py-2.5 px-3 font-semibold ${sevColor}">${tr.severity}</td>
            <td class="py-2.5 px-3">Frame ${tr.first_frame} &rarr; ${tr.last_frame} (${tr.duration_frames} f)</td>
            <td class="py-2.5 px-3 font-semibold">${(tr.max_confidence * 100).toFixed(0)}%</td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// 5. INSPECTION HISTORY & MODAL
// ==========================================
async function loadInspectionHistory() {
    const tbody = document.getElementById("history-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500">Loading survey records...</td></tr>`;

    try {
        const res = await fetch("/api/inspections?limit=50");
        const data = await res.json();
        tbody.innerHTML = "";

        if (data.inspections.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-500">No inspections recorded yet.</td></tr>`;
            return;
        }

        data.inspections.forEach(ins => {
            let riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400">${ins.risk_score} (Low)</span>`;
            if (ins.risk_level === "Moderate") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400">${ins.risk_score} (Moderate)</span>`;
            if (ins.risk_level === "High") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-orange-500/20 text-orange-400">${ins.risk_score} (High)</span>`;
            if (ins.risk_level === "Critical") riskBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-400">${ins.risk_score} (Critical)</span>`;

            const row = document.createElement("tr");
            row.className = "border-b border-slate-800 hover:bg-slate-800/40 text-sm transition";
            row.innerHTML = `
                <td class="py-3 px-4 font-mono text-xs text-blue-400 font-semibold">${ins.code}</td>
                <td class="py-3 px-4 font-medium text-slate-200">${ins.road_name}</td>
                <td class="py-3 px-4 text-xs text-slate-400">${ins.upload_time ? ins.upload_time.slice(0, 10) : 'N/A'}</td>
                <td class="py-3 px-4 uppercase text-xs font-mono text-slate-400">${ins.media_type}</td>
                <td class="py-3 px-4 font-bold">${ins.unique_defects_count}</td>
                <td class="py-3 px-4">${riskBadge}</td>
                <td class="py-3 px-4 text-right space-x-2">
                    <button onclick="viewInspectionDetail(${ins.id})" class="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white rounded">
                        View
                    </button>
                    <button onclick="downloadReport(${ins.id}, 'pdf')" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded border border-slate-700">
                        PDF
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error(e);
    }
}

async function viewInspectionDetail(inspId) {
    try {
        const res = await fetch(`/api/inspections/${inspId}`);
        const ins = await res.json();

        document.getElementById("modal-title").textContent = `${ins.code} - ${ins.road_name}`;
        document.getElementById("modal-image").src = ins.annotated_url || "";
        document.getElementById("modal-road").textContent = `${ins.road_name} (${ins.road_type}, Speed: ${ins.speed_limit} km/h)`;
        document.getElementById("modal-coords").textContent = `${ins.latitude || 'N/A'}, ${ins.longitude || 'N/A'}`;
        document.getElementById("modal-risk").textContent = `${ins.risk_score} / 100 (${ins.risk_level} Risk)`;

        const tbody = document.getElementById("modal-defects-body");
        tbody.innerHTML = "";
        ins.defects.forEach(d => {
            const row = document.createElement("tr");
            row.className = "border-b border-slate-800 text-xs";
            row.innerHTML = `
                <td class="py-2 px-3 font-mono text-blue-400">${d.track_id}</td>
                <td class="py-2 px-3 font-medium text-slate-200">${d.class_name}</td>
                <td class="py-2 px-3 font-semibold">${d.severity}</td>
                <td class="py-2 px-3">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-2 px-3">${d.verification_status}</td>
            `;
            tbody.appendChild(row);
        });

        // Set export buttons
        document.getElementById("btn-modal-pdf").onclick = () => downloadReport(ins.id, "pdf");
        document.getElementById("btn-modal-csv").onclick = () => downloadReport(ins.id, "csv");
        document.getElementById("btn-modal-json").onclick = () => downloadReport(ins.id, "json");

        document.getElementById("inspection-modal").classList.remove("hidden");
    } catch (e) {
        console.error(e);
        alert("Failed to fetch inspection details.");
    }
}

function closeModal() {
    document.getElementById("inspection-modal").classList.add("hidden");
}

function downloadReport(inspId, format) {
    window.open(`/api/reports/${inspId}/export/${format}`, "_blank");
}

// ==========================================
// 6. DUPLICATE DAMAGE DETECTION
// ==========================================
async function loadDuplicates() {
    const container = document.getElementById("duplicates-container");
    if (!container) return;
    container.innerHTML = `<div class="p-8 text-center text-slate-500">Scanning for cross-inspection duplicates...</div>`;

    try {
        const res = await fetch("/api/duplicates");
        const data = await res.json();
        container.innerHTML = "";

        if (data.duplicates.length === 0) {
            container.innerHTML = `
                <div class="glass-card p-8 text-center">
                    <div class="text-emerald-400 font-bold text-lg mb-1">No Duplicate Defects Pending</div>
                    <div class="text-sm text-slate-400">All uploaded inspections correspond to unique physical coordinates.</div>
                </div>
            `;
            return;
        }

        data.duplicates.forEach(dup => {
            const card = document.createElement("div");
            card.className = "glass-card p-5 mb-4 border-l-4 border-amber-500";
            card.innerHTML = `
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-400 uppercase">Duplicate Alert</span>
                        <h4 class="text-base font-bold text-slate-200 mt-1">Spatial Proximity: ${dup.spatial_distance_m} meters</h4>
                    </div>
                    <div class="text-right">
                        <span class="text-xs text-slate-400">Visual Hash Match:</span>
                        <div class="text-lg font-bold text-emerald-400">${dup.visual_similarity_pct}%</div>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4 bg-slate-900/60 p-3 rounded-lg mb-4 text-xs">
                    <div>
                        <div class="text-slate-400 font-semibold mb-1">New Defect Submission:</div>
                        <div class="font-mono text-cyan-400">${dup.new_defect.track_id} (${dup.new_defect.category})</div>
                        <div class="text-slate-300">Severity: ${dup.new_defect.severity}</div>
                    </div>
                    <div>
                        <div class="text-slate-400 font-semibold mb-1">Existing Historical Defect:</div>
                        <div class="font-mono text-blue-400">${dup.existing_defect.track_id} (${dup.existing_defect.category})</div>
                        <div class="text-slate-300">Severity: ${dup.existing_defect.severity}</div>
                    </div>
                </div>

                <div class="flex justify-end space-x-3">
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'Dismissed')" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded border border-slate-700">
                        Dismiss (Different Defects)
                    </button>
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'Merged')" class="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-xs font-semibold text-white rounded">
                        Confirm & Merge Duplicate
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error(e);
    }
}

async function resolveDuplicateMatch(matchId, action) {
    try {
        const formData = new FormData();
        formData.append("action", action);
        const res = await fetch(`/api/duplicates/${matchId}/resolve`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            loadDuplicates();
        }
    } catch (e) {
        console.error(e);
    }
}

// ==========================================
// 7. REPAIR LIFECYCLE MANAGEMENT
// ==========================================
async function loadRepairs() {
    const colReported = document.getElementById("repair-col-reported");
    const colProgress = document.getElementById("repair-col-progress");
    const colRepaired = document.getElementById("repair-col-repaired");
    if (!colReported) return;

    colReported.innerHTML = "";
    colProgress.innerHTML = "";
    colRepaired.innerHTML = "";

    try {
        const res = await fetch("/api/repairs");
        const data = await res.json();

        data.repairs.forEach(rep => {
            const card = document.createElement("div");
            card.className = "glass-card p-3.5 mb-3 text-xs";
            card.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <span class="font-bold text-slate-200">#REP-${rep.id}</span>
                    <span class="px-2 py-0.5 rounded font-semibold ${rep.priority === 'Emergency' ? 'bg-rose-500/20 text-rose-400' : 'bg-blue-500/20 text-blue-400'}">
                        ${rep.priority}
                    </span>
                </div>
                <div class="text-slate-300 font-medium mb-1">${rep.assigned_authority}</div>
                ${rep.assigned_contractor ? `<div class="text-slate-400 mb-2">Contractor: ${rep.assigned_contractor}</div>` : ''}
                <div class="text-slate-400 mb-3">${rep.remarks || 'Routine maintenance dispatch.'}</div>

                <div class="flex justify-between items-center pt-2 border-t border-slate-800">
                    <span class="text-slate-500 font-mono">${rep.created_at ? rep.created_at.slice(0, 10) : ''}</span>
                    <button onclick="promptUpdateRepair(${rep.id})" class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-blue-400 font-semibold rounded border border-slate-700">
                        Update Status
                    </button>
                </div>
            `;

            if (rep.status === "Detected" || rep.status === "Reported") {
                colReported.appendChild(card);
            } else if (rep.status === "Repair in Progress" || rep.status === "Assigned") {
                colProgress.appendChild(card);
            } else {
                colRepaired.appendChild(card);
            }
        });
    } catch (e) {
        console.error(e);
    }
}

async function promptUpdateRepair(repId) {
    const nextStatus = prompt("Enter new status (Assigned, Repair in Progress, Repaired, Closed):", "Repaired");
    if (!nextStatus) return;

    const formData = new FormData();
    formData.append("status", nextStatus);
    formData.append("remarks", "Updated via Municipal Dispatch Portal");

    try {
        const res = await fetch(`/api/repairs/${repId}/update`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            loadRepairs();
            loadDashboardAnalytics();
        }
    } catch (e) {
        console.error(e);
    }
}

// ==========================================
// 8. MANUAL VERIFICATION PORTAL
// ==========================================
async function loadUnverifiedDefects() {
    const tbody = document.getElementById("verification-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-500">Loading unverified detections...</td></tr>`;

    try {
        const res = await fetch("/api/defects?limit=50");
        const data = await res.json();
        tbody.innerHTML = "";

        const unverified = data.defects.filter(d => d.verification_status === "Unverified");
        if (unverified.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-emerald-400 font-semibold">All defect detections have been verified!</td></tr>`;
            return;
        }

        unverified.forEach(d => {
            const row = document.createElement("tr");
            row.className = "border-b border-slate-800 text-xs";
            row.innerHTML = `
                <td class="py-3 px-4 font-mono font-bold text-blue-400">${d.track_id}</td>
                <td class="py-3 px-4 font-medium text-slate-200">${d.class_name} (${d.category_code})</td>
                <td class="py-3 px-4 font-semibold">${d.severity}</td>
                <td class="py-3 px-4">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-3 px-4 text-slate-400">${d.latitude ? `${d.latitude}, ${d.longitude}` : 'No GPS'}</td>
                <td class="py-3 px-4 text-right space-x-2">
                    <button onclick="submitDefectVerification(${d.id}, 'Verified')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded">
                        Approve
                    </button>
                    <button onclick="submitDefectVerification(${d.id}, 'Rejected')" class="px-3 py-1 bg-rose-600/30 hover:bg-rose-600 text-rose-300 font-semibold rounded border border-rose-500/40">
                        Reject False Positive
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error(e);
    }
}

async function submitDefectVerification(defectId, action) {
    const formData = new FormData();
    formData.append("action", action);
    formData.append("reviewer", "Municipal Audit Engineer");

    try {
        const res = await fetch(`/api/defects/${defectId}/verify`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            loadUnverifiedDefects();
        }
    } catch (e) {
        console.error(e);
    }
}

// ==========================================
// 9. MODEL BENCHMARK METRICS
// ==========================================
async function loadBenchmarkMetrics() {
    try {
        const res = await fetch("/api/models/benchmark");
        const data = await res.json();
        const tbody = document.getElementById("benchmark-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        for (const [mname, mdata] of Object.entries(data)) {
            const row = document.createElement("tr");
            row.className = "border-b border-slate-800 text-xs";
            row.innerHTML = `
                <td class="py-3 px-4 font-bold text-slate-200">${mname}</td>
                <td class="py-3 px-4 font-mono text-slate-400">${mdata.model_file}</td>
                <td class="py-3 px-4 font-bold text-emerald-400">${(mdata.precision * 100).toFixed(1)}%</td>
                <td class="py-3 px-4 font-bold text-blue-400">${(mdata.recall * 100).toFixed(1)}%</td>
                <td class="py-3 px-4 font-bold">${mdata.f1_score.toFixed(4)}</td>
                <td class="py-3 px-4 font-bold text-cyan-400">${mdata.map50.toFixed(4)}</td>
                <td class="py-3 px-4">${mdata.avg_latency_ms} ms (${mdata.fps} FPS)</td>
            `;
            tbody.appendChild(row);
        }
    } catch (e) {
        console.error(e);
    }
}
