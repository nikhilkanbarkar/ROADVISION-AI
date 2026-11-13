/**
 * ROADVISION AI - Central Application Controller (White Theme & RBAC Edition)
 * Handles role-based dual-sided access (Citizen End vs Authority End),
 * AI image & video inspections, persistent ByteTrack tracking,
 * citizen grievance reporting, duplicate resolution, and municipal reporting.
 */

let categoryChart = null;
let severityChart = null;
let activeInspectionId = null;

// User Session & Role State
let currentUser = {
    role: "authority", // "citizen" or "authority"
    name: "Er. Rajesh Verma",
    email: "authority@pwd.gov.in",
    title: "Chief Municipal Engineer",
    badge: "Civil Authority (Full Access)"
};

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();
    initRoleSession();
    setupDropzone();
    setupVideoDropzone();
    setupCitizenDropzone();
});

// ==========================================
// 1. ROLE-BASED ACCESS CONTROL (RBAC) & SIGN-IN
// ==========================================
function initRoleSession() {
    const savedRole = localStorage.getItem("roadvision_role") || "authority";
    const savedName = localStorage.getItem("roadvision_name");
    const savedEmail = localStorage.getItem("roadvision_email");

    if (savedRole === "citizen") {
        currentUser = {
            role: "citizen",
            name: savedName || "Priya Sharma",
            email: savedEmail || "citizen@roadvision.in",
            title: "Citizen Reporter & Motorist",
            badge: "Public User (Citizen End)"
        };
    } else {
        currentUser = {
            role: "authority",
            name: savedName || "Er. Rajesh Verma",
            email: savedEmail || "authority@pwd.gov.in",
            title: "Chief Municipal Engineer",
            badge: "Civil Authority (Full Access)"
        };
    }
    applyRolePermissions(currentUser.role);
}

function openSignInModal() {
    const modal = document.getElementById("signin-modal");
    if (modal) {
        modal.classList.remove("hidden");
        switchLoginRoleTab(currentUser.role || "authority");
    }
}

function closeSignInModal() {
    const modal = document.getElementById("signin-modal");
    if (modal) modal.classList.add("hidden");
}

function switchLoginRoleTab(role) {
    const btnCitizen = document.getElementById("modal-tab-citizen");
    const btnAuth = document.getElementById("modal-tab-authority");
    const panelCitizen = document.getElementById("login-panel-citizen");
    const panelAuth = document.getElementById("login-panel-authority");

    if (role === "citizen") {
        btnCitizen.className = "py-2.5 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-white text-emerald-800 shadow-sm border border-slate-200";
        btnAuth.className = "py-2.5 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-600 hover:text-slate-900";
        panelCitizen.classList.remove("hidden");
        panelAuth.classList.add("hidden");
    } else {
        btnAuth.className = "py-2.5 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 bg-white text-blue-700 shadow-sm border border-slate-200";
        btnCitizen.className = "py-2.5 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 text-slate-600 hover:text-slate-900";
        panelAuth.classList.remove("hidden");
        panelCitizen.classList.add("hidden");
    }
    if (window.lucide) lucide.createIcons();
}

async function performSignIn(role) {
    try {
        const formData = new FormData();
        formData.append("role", role);
        if (role === "citizen") {
            const name = document.getElementById("citizen-login-name").value || "Priya Sharma";
            const email = document.getElementById("citizen-login-email").value || "citizen@roadvision.in";
            formData.append("identifier", email);
            currentUser = {
                role: "citizen",
                name: name,
                email: email,
                title: "Citizen Reporter & Motorist",
                badge: "Public User (Citizen End)"
            };
        } else {
            const email = document.getElementById("auth-login-email").value || "authority@pwd.gov.in";
            formData.append("identifier", email);
            currentUser = {
                role: "authority",
                name: "Er. Rajesh Verma",
                email: email,
                title: "Chief Municipal Engineer",
                badge: "Civil Authority (Full Access)"
            };
        }

        localStorage.setItem("roadvision_role", currentUser.role);
        localStorage.setItem("roadvision_name", currentUser.name);
        localStorage.setItem("roadvision_email", currentUser.email);

        await fetch("/api/auth/login", { method: "POST", body: formData });
    } catch(e) {
        console.warn("Auth endpoint fallback:", e);
    }

    applyRolePermissions(currentUser.role);
    closeSignInModal();
}

function applyRolePermissions(role) {
    const navCitizen = document.getElementById("sidebar-citizen-nav");
    const navAuth = document.getElementById("sidebar-authority-nav");
    const rolePill = document.getElementById("active-role-pill");
    const roleDot = document.getElementById("role-dot");
    const roleLabel = document.getElementById("role-label");
    const nameBadge = document.getElementById("user-name-badge");
    const profileAvatar = document.getElementById("profile-avatar-circle");
    const profileName = document.getElementById("profile-name");
    const profileSub = document.getElementById("profile-role-sub");

    if (role === "citizen") {
        if (navCitizen) navCitizen.classList.remove("hidden");
        if (navAuth) navAuth.classList.add("hidden");

        rolePill.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold shadow-sm transition-all bg-emerald-50 text-emerald-800 border-emerald-300";
        roleDot.className = "w-2.5 h-2.5 rounded-full bg-emerald-600 animate-pulse";
        roleLabel.textContent = "Citizen / Public End";
        nameBadge.textContent = `• ${currentUser.name}`;

        profileAvatar.className = "w-9 h-9 rounded-full bg-emerald-600 text-white font-black text-sm flex items-center justify-center shrink-0 shadow-sm";
        profileAvatar.textContent = "PS";
        profileName.textContent = currentUser.name;
        profileSub.textContent = "Citizen Reporter";
        profileSub.className = "text-[11px] text-emerald-700 font-semibold truncate";

        switchTab("citizen-report");
    } else {
        if (navCitizen) navCitizen.classList.add("hidden");
        if (navAuth) navAuth.classList.remove("hidden");

        rolePill.className = "flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold shadow-sm transition-all bg-blue-50 text-blue-700 border-blue-200";
        roleDot.className = "w-2.5 h-2.5 rounded-full bg-blue-600 animate-pulse";
        roleLabel.textContent = "Civil Authority End";
        nameBadge.textContent = `• ${currentUser.name}`;

        profileAvatar.className = "w-9 h-9 rounded-full bg-blue-600 text-white font-black text-sm flex items-center justify-center shrink-0 shadow-sm";
        profileAvatar.textContent = "RV";
        profileName.textContent = currentUser.name;
        profileSub.textContent = "Chief Municipal Engineer";
        profileSub.className = "text-[11px] text-blue-700 font-semibold truncate";

        switchTab("overview");
    }

    if (window.lucide) lucide.createIcons();
}

// ==========================================
// 2. NAVIGATION & TAB SWITCHING
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
    // Reset all nav styling to clean light slate
    document.querySelectorAll(".nav-item").forEach(el => {
        el.classList.remove("bg-blue-50", "text-blue-700", "border-l-4", "border-blue-600", "shadow-sm", "bg-emerald-50", "text-emerald-800", "border-emerald-600");
        el.classList.add("text-slate-600");
    });

    const activeNav = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
    if (activeNav) {
        if (tabId.startsWith("citizen-")) {
            activeNav.classList.add("bg-emerald-50", "text-emerald-800", "border-l-4", "border-emerald-600", "shadow-sm");
        } else {
            activeNav.classList.add("bg-blue-50", "text-blue-700", "border-l-4", "border-blue-600", "shadow-sm");
        }
        activeNav.classList.remove("text-slate-600");
    }

    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    const targetContent = document.getElementById(`tab-${tabId}`);
    if (targetContent) {
        targetContent.classList.add("active");
    }

    // Lazy load tab specific components
    if (tabId === "map") {
        setTimeout(initRoadMap, 150);
    } else if (tabId === "citizen-map") {
        setTimeout(initCitizenMap, 150);
    } else if (tabId === "citizen-myreports") {
        loadCitizenReports();
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

    if (window.lucide) lucide.createIcons();
}

// ==========================================
// 3. CITIZEN END: REPORTING PIPELINE
// ==========================================
let citizenSelectedFile = null;

function setupCitizenDropzone() {
    const dropzone = document.getElementById("citizen-dropzone");
    const fileInput = document.getElementById("citizen-file-input");
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("border-emerald-500", "bg-emerald-50/50");
    });
    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("border-emerald-500", "bg-emerald-50/50");
    });
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-emerald-500", "bg-emerald-50/50");
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleCitizenFileSelected(fileInput.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleCitizenFileSelected(fileInput.files[0]);
        }
    });
}

function handleCitizenFileSelected(file) {
    if (!file) return;
    citizenSelectedFile = file;

    const preview = document.getElementById("citizen-img-preview");
    const promptBox = document.getElementById("citizen-dropzone-prompt");
    const badge = document.getElementById("citizen-file-badge");

    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
    badge.textContent = `Selected: ${file.name} (${sizeMB} MB) - Ready for AI Scan`;
    badge.classList.remove("hidden");

    if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.classList.remove("hidden");
            promptBox.classList.add("hidden");
        };
        reader.readAsDataURL(file);
    } else {
        preview.classList.add("hidden");
        promptBox.classList.remove("hidden");
    }
}

function detectCitizenGPS() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude.toFixed(5);
                const lon = pos.coords.longitude.toFixed(5);
                document.getElementById("citizen-coords").value = `${lat}, ${lon}`;
            },
            (err) => {
                alert("GPS permission denied or unavailable. Using default Sector 29 coordinates.");
                document.getElementById("citizen-coords").value = "28.4712, 77.0725";
            }
        );
    } else {
        document.getElementById("citizen-coords").value = "28.4712, 77.0725";
    }
}

async function submitCitizenReport() {
    const fileInput = document.getElementById("citizen-file-input");
    if (!citizenSelectedFile && (!fileInput.files || fileInput.files.length === 0)) {
        alert("Please tap to select or drop a road photo or video first.");
        return;
    }

    const file = citizenSelectedFile || fileInput.files[0];
    const btn = document.getElementById("btn-citizen-submit");
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">&#9696;</span> AI Analyzing & Generating Grievance Ticket...`;

    const roadName = document.getElementById("citizen-road-name").value || "MG Road, Sector 29";
    const speed = document.getElementById("citizen-speed").value || "60";
    const coordsStr = document.getElementById("citizen-coords").value || "28.4712, 77.0725";
    const [lat, lon] = coordsStr.split(",").map(s => parseFloat(s.trim()));

    const isVideo = file.type.startsWith("video/") || file.name.match(/\.(mp4|avi|mov|mkv)$/i);
    const endpoint = isVideo ? "/api/inspect/video" : "/api/inspect/image";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("road_name", roadName);
    formData.append("road_type", "Arterial");
    formData.append("speed_limit", speed);
    formData.append("weather", "Clear/Dry");
    formData.append("traffic", "Moderate");
    if (!isNaN(lat) && !isNaN(lon)) {
        formData.append("manual_lat", lat);
        formData.append("manual_lon", lon);
    }

    try {
        const res = await fetch(endpoint, { method: "POST", body: formData });
        const data = await res.json();

        if (data.status === "success") {
            displayCitizenReportResult(data, roadName);
        } else {
            alert("Submission error: " + (data.detail || "Unable to process report"));
        }
    } catch(e) {
        console.error("Citizen submission error:", e);
        alert("Report submission failed. Please check network and retry.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="send" class="w-4 h-4"></i><span>Submit Grievance to Authority</span>`;
        if (window.lucide) lucide.createIcons();
    }
}

function displayCitizenReportResult(data, roadName) {
    const resultCard = document.getElementById("citizen-result-card");
    resultCard.classList.remove("hidden");

    document.getElementById("citizen-ticket-number").textContent = `#CIT-${data.code}`;
    const imgElem = document.getElementById("citizen-annotated-img");
    imgElem.src = data.annotated_url || data.original_url || "";

    const alertBox = document.getElementById("citizen-risk-alert-box");
    const headline = document.getElementById("citizen-risk-headline");
    const desc = document.getElementById("citizen-risk-desc");

    const totalDef = data.total_detections || data.unique_defects || 0;
    const score = data.risk_score || 0;

    if (totalDef === 0) {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-emerald-50 border-emerald-200 text-emerald-900";
        headline.textContent = "Road Condition Verified: Sound Pavement";
        desc.textContent = "No critical pothole cavities were detected by the AI inspection engine on this image. PWD road maintenance log updated.";
    } else if (score >= 50) {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-rose-50 border-rose-200 text-rose-900";
        headline.textContent = `Caution: High Risk Road Defect Verified (Score ${score}/100)`;
        desc.textContent = `AI detected ${totalDef} road surface defect(s) on ${roadName}. A high-priority grievance order has been queued for municipal asphalt patching.`;
    } else {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-amber-50 border-amber-200 text-amber-900";
        headline.textContent = `Moderate Distress Verified (Score ${score}/100)`;
        desc.textContent = `AI identified minor/moderate distress on ${roadName}. Complaint dispatched to regular zonal maintenance.`;
    }

    resultCard.scrollIntoView({ behavior: "smooth" });
}

async function loadCitizenReports() {
    const listContainer = document.getElementById("citizen-myreports-list");
    if (!listContainer) return;
    listContainer.innerHTML = `<div class="p-8 text-center text-slate-500">Loading your reported grievances...</div>`;

    try {
        const res = await fetch("/api/citizen/my-reports");
        const data = await res.json();
        listContainer.innerHTML = "";

        if (!data.reports || data.reports.length === 0) {
            listContainer.innerHTML = `
                <div class="text-center py-10 bg-slate-50 rounded-xl border border-slate-200">
                    <i data-lucide="inbox" class="w-10 h-10 text-slate-400 mx-auto mb-2"></i>
                    <div class="font-bold text-slate-800">No Citizen Reports Yet</div>
                    <div class="text-xs text-slate-500 mt-1">Submit your first road distress report via the "Report Road Damage" tab.</div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        data.reports.forEach(rep => {
            const card = document.createElement("div");
            card.className = "p-5 bg-white rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition space-y-4";
            card.innerHTML = `
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-mono text-xs font-black text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">${rep.ticket_code}</span>
                            <span class="text-xs text-slate-500 font-medium">${rep.upload_date}</span>
                        </div>
                        <h4 class="text-base font-bold text-slate-900 mt-1">${rep.road_name}</h4>
                    </div>
                    <div>
                        <span class="px-3 py-1 rounded-full text-xs font-bold ${rep.status_class}">${rep.status}</span>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div>
                        <span class="text-slate-500 font-bold">Observed Distress:</span>
                        <div class="font-semibold text-slate-800 mt-0.5">${rep.defect_count} defect(s) (${rep.severity})</div>
                    </div>
                    <div>
                        <span class="text-slate-500 font-bold">Safety Risk Tier:</span>
                        <div class="font-bold text-amber-700 mt-0.5">${rep.risk_score} / 100 (${rep.risk_level})</div>
                    </div>
                    <div>
                        <span class="text-slate-500 font-bold">Action Remarks:</span>
                        <div class="text-slate-600 mt-0.5 truncate">${rep.remarks}</div>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div>
                    <div class="flex justify-between text-[11px] font-bold text-slate-600 mb-1">
                        <span>Municipal Resolution Progress</span>
                        <span>${rep.progress_pct}%</span>
                    </div>
                    <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                        <div class="h-full rounded-full transition-all duration-500 ${rep.progress_pct >= 100 ? 'bg-emerald-600' : 'bg-blue-600'}" style="width: ${rep.progress_pct}%"></div>
                    </div>
                </div>
            `;
            listContainer.appendChild(card);
        });

        if (window.lucide) lucide.createIcons();
    } catch(e) {
        console.error("Error loading citizen reports:", e);
    }
}

// ==========================================
// 4. AUTHORITY END: DASHBOARD & ANALYTICS
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

        // Render Charts with Light Theme Typography
        renderCategoryChart(data.category_distribution);
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
                backgroundColor: ['#2563eb', '#059669', '#d97706', '#dc2626'],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#475569', font: { size: 11, weight: 'bold' }, boxWidth: 12 } }
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
                backgroundColor: ['#059669', '#d97706', '#dc2626'],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(0, 0, 0, 0.06)' }, ticks: { color: '#64748b', font: { weight: 'bold' } } },
                x: { grid: { display: false }, ticks: { color: '#475569', font: { weight: 'bold' } } }
            }
        }
    });
}

function renderRecentSurveys(recentList) {
    const tbody = document.getElementById("recent-surveys-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!recentList || recentList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No surveys recorded yet.</td></tr>`;
        return;
    }

    recentList.forEach(item => {
        let riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">Low</span>`;
        if (item.risk_level === "Moderate") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">Moderate</span>`;
        if (item.risk_level === "High") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-50 text-orange-700 border border-orange-200">High</span>`;
        if (item.risk_level === "Critical") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">Critical</span>`;

        const row = document.createElement("tr");
        row.className = "hover:bg-slate-50 transition border-b border-slate-100";
        row.innerHTML = `
            <td class="py-3 px-4 font-mono text-xs text-blue-700 font-bold">${item.code}</td>
            <td class="py-3 px-4 font-bold text-slate-800">${item.road_name}</td>
            <td class="py-3 px-4 text-xs uppercase text-slate-500 font-medium">${item.media_type}</td>
            <td class="py-3 px-4 text-sm font-black text-slate-900">${item.unique_defects}</td>
            <td class="py-3 px-4">${riskBadge}</td>
            <td class="py-3 px-4 text-right">
                <button onclick="viewInspectionDetail(${item.id})" class="px-3 py-1 bg-white hover:bg-slate-100 text-xs font-bold text-slate-700 rounded-lg border border-slate-300 shadow-sm">
                    Inspect
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// 5. AUTHORITY END: IMAGE INSPECTION
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
        score <= 25 ? "bg-emerald-600" : (score <= 50 ? "bg-amber-600" : (score <= 75 ? "bg-orange-600" : "bg-rose-600"))
    );

    // Populate Defect Table
    const tbody = document.getElementById("img-defects-table-body");
    tbody.innerHTML = "";

    if (data.defects.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-slate-500">No defects detected. Road pavement is in sound condition.</td></tr>`;
    } else {
        data.defects.forEach(d => {
            let sevColor = d.severity === "Minor" ? "text-emerald-700" : (d.severity === "Moderate" ? "text-amber-700" : "text-rose-700 font-bold");
            const row = document.createElement("tr");
            row.className = "border-b border-slate-100 text-xs";
            row.innerHTML = `
                <td class="py-2.5 px-3 font-mono font-bold text-blue-700">${d.track_id}</td>
                <td class="py-2.5 px-3 font-bold text-slate-800">${d.display_name} (${d.category_code})</td>
                <td class="py-2.5 px-3 ${sevColor}">${d.severity}</td>
                <td class="py-2.5 px-3 font-medium text-slate-700">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-2.5 px-3 font-medium text-slate-700">${(d.relative_area * 100).toFixed(2)}%</td>
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

    activeInspectionId = data.inspection_id;
}

// ==========================================
// 6. AUTHORITY END: VIDEO INSPECTION & TRACKING
// ==========================================
function setupVideoDropzone() {
    const dropzone = document.getElementById("video-dropzone");
    const fileInput = document.getElementById("video-file-input");
    if (!dropzone || !fileInput) return;

    dropzone.addEventListener("click", (e) => {
        if (e.target.tagName.toLowerCase() === "video") return;
        fileInput.click();
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("border-cyan-600", "bg-cyan-50/50");
    });
    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("border-cyan-600", "bg-cyan-50/50");
    });
    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("border-cyan-600", "bg-cyan-50/50");
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
        selectedMeta.textContent = `Size: ${sizeMB} MB | Status: Ready for ByteTrack AI analysis`;
    }
    if (selectedInfo) selectedInfo.classList.remove("hidden");
    if (btnText) btnText.textContent = `Process & Track Video (${sizeMB} MB)`;

    if (videoPreview) {
        try {
            const url = URL.createObjectURL(file);
            videoPreview.src = url;
            videoPreview.classList.remove("hidden");
            videoPreview.load();
        } catch (e) {
            console.warn("Video preview error:", e);
        }
    }

    if (window.lucide) lucide.createIcons();
}

async function runVideoInspection() {
    const fileInput = document.getElementById("video-file-input");
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select or drop a road survey video file first.");
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
    if (progressText) progressText.textContent = `Uploading & tracking video (${sizeMB} MB)...`;
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
        const res = await fetch("/api/inspect/video", { method: "POST", body: formData });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `Server responded with HTTP ${res.status}`);
        }
        const data = await res.json();
        if (data.status === "success") {
            displayVideoInspectionResults(data);
        } else {
            alert("Video warning: " + (data.detail || "Unknown error occurred"));
        }
    } catch (e) {
        console.error("Video error:", e);
        alert(`Video processing failed: ${e.message}`);
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
        let sevColor = tr.severity === "Minor" ? "text-emerald-700 font-bold" : (tr.severity === "Moderate" ? "text-amber-700 font-bold" : "text-rose-700 font-bold");
        const row = document.createElement("tr");
        row.className = "border-b border-slate-100 text-xs";
        row.innerHTML = `
            <td class="py-2.5 px-3 font-mono font-bold text-cyan-700">${tr.track_id}</td>
            <td class="py-2.5 px-3 font-bold text-slate-800">${tr.display_name}</td>
            <td class="py-2.5 px-3 ${sevColor}">${tr.severity}</td>
            <td class="py-2.5 px-3 text-slate-600 font-medium">Frames ${tr.first_frame} &rarr; ${tr.last_frame} (${tr.duration_frames} f)</td>
            <td class="py-2.5 px-3 font-bold text-slate-800">${(tr.max_confidence * 100).toFixed(0)}%</td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// 7. INSPECTION HISTORY & MODAL
// ==========================================
async function loadInspectionHistory() {
    const tbody = document.getElementById("history-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">Loading survey records...</td></tr>`;

    try {
        const res = await fetch("/api/inspections?limit=50");
        const data = await res.json();
        tbody.innerHTML = "";

        if (data.inspections.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">No inspections recorded yet.</td></tr>`;
            return;
        }

        data.inspections.forEach(ins => {
            let riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">${ins.risk_score} (Low)</span>`;
            if (ins.risk_level === "Moderate") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-700 border border-amber-200">${ins.risk_score} (Moderate)</span>`;
            if (ins.risk_level === "High") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-orange-50 text-orange-700 border border-orange-200">${ins.risk_score} (High)</span>`;
            if (ins.risk_level === "Critical") riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">${ins.risk_score} (Critical)</span>`;

            const row = document.createElement("tr");
            row.className = "hover:bg-slate-50 text-sm transition border-b border-slate-100";
            row.innerHTML = `
                <td class="py-3 px-4 font-mono text-xs text-blue-700 font-bold">${ins.code}</td>
                <td class="py-3 px-4 font-bold text-slate-800">${ins.road_name}</td>
                <td class="py-3 px-4 text-xs text-slate-500">${ins.upload_time ? ins.upload_time.slice(0, 10) : 'N/A'}</td>
                <td class="py-3 px-4 uppercase text-xs font-bold font-mono text-slate-500">${ins.media_type}</td>
                <td class="py-3 px-4 font-black text-slate-900">${ins.unique_defects_count}</td>
                <td class="py-3 px-4">${riskBadge}</td>
                <td class="py-3 px-4 text-right space-x-2">
                    <button onclick="viewInspectionDetail(${ins.id})" class="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-xs font-bold text-white rounded-lg shadow-sm">
                        View
                    </button>
                    <button onclick="downloadReport(${ins.id}, 'pdf')" class="px-2.5 py-1 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 rounded-lg border border-slate-300 shadow-sm">
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
            row.className = "border-b border-slate-100 text-xs";
            row.innerHTML = `
                <td class="py-2.5 px-3 font-mono font-bold text-blue-700">${d.track_id}</td>
                <td class="py-2.5 px-3 font-bold text-slate-800">${d.class_name}</td>
                <td class="py-2.5 px-3 font-semibold text-slate-700">${d.severity}</td>
                <td class="py-2.5 px-3 text-slate-700">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-2.5 px-3 font-bold text-emerald-700">${d.verification_status}</td>
            `;
            tbody.appendChild(row);
        });

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
// 8. DUPLICATE DAMAGE DETECTION
// ==========================================
async function loadDuplicates() {
    const container = document.getElementById("duplicates-container");
    if (!container) return;
    container.innerHTML = `<div class="p-8 text-center text-slate-400 font-medium">Scanning for cross-inspection duplicates...</div>`;

    try {
        const res = await fetch("/api/duplicates");
        const data = await res.json();
        container.innerHTML = "";

        if (data.duplicates.length === 0) {
            container.innerHTML = `
                <div class="glass-card p-8 text-center bg-white border border-slate-200">
                    <div class="text-emerald-700 font-extrabold text-lg mb-1">No Duplicate Defects Pending</div>
                    <div class="text-sm text-slate-500">All uploaded inspections correspond to unique physical coordinates.</div>
                </div>
            `;
            return;
        }

        data.duplicates.forEach(dup => {
            const card = document.createElement("div");
            card.className = "glass-card p-5 mb-4 border-l-4 border-amber-500 bg-white shadow-sm";
            card.innerHTML = `
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-50 text-amber-800 border border-amber-200 uppercase">Duplicate Alert</span>
                        <h4 class="text-base font-bold text-slate-900 mt-1">Spatial Proximity: ${dup.spatial_distance_m} meters</h4>
                    </div>
                    <div class="text-right">
                        <span class="text-xs text-slate-500 font-semibold">Visual Hash Match:</span>
                        <div class="text-lg font-black text-emerald-700">${dup.visual_similarity_pct}%</div>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-xl mb-4 text-xs border border-slate-200">
                    <div>
                        <div class="text-slate-500 font-bold mb-1">New Defect Submission:</div>
                        <div class="font-mono text-cyan-700 font-bold">${dup.new_defect.track_id} (${dup.new_defect.category})</div>
                        <div class="text-slate-700 font-medium">Severity: ${dup.new_defect.severity}</div>
                    </div>
                    <div>
                        <div class="text-slate-500 font-bold mb-1">Existing Historical Defect:</div>
                        <div class="font-mono text-blue-700 font-bold">${dup.existing_defect.track_id} (${dup.existing_defect.category})</div>
                        <div class="text-slate-700 font-medium">Severity: ${dup.existing_defect.severity}</div>
                    </div>
                </div>

                <div class="flex justify-end space-x-3">
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'Dismissed')" class="px-3 py-1.5 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 rounded-lg border border-slate-300 shadow-sm">
                        Dismiss (Different Defects)
                    </button>
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'Merged')" class="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-xs font-bold text-white rounded-lg shadow-sm">
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
// 9. REPAIR LIFECYCLE MANAGEMENT
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
            card.className = "glass-card p-4 mb-3 text-xs bg-white shadow-sm border border-slate-200";
            card.innerHTML = `
                <div class="flex justify-between items-start mb-2">
                    <span class="font-mono font-bold text-slate-900">#REP-${rep.id}</span>
                    <span class="px-2 py-0.5 rounded-full font-bold ${rep.priority === 'Emergency' ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}">
                        ${rep.priority}
                    </span>
                </div>
                <div class="text-slate-800 font-bold mb-1">${rep.assigned_authority}</div>
                ${rep.assigned_contractor ? `<div class="text-slate-600 mb-2 font-medium">Contractor: ${rep.assigned_contractor}</div>` : ''}
                <div class="text-slate-500 mb-3">${rep.remarks || 'Routine maintenance dispatch.'}</div>

                <div class="flex justify-between items-center pt-2.5 border-t border-slate-100">
                    <span class="text-slate-400 font-mono text-[11px]">${rep.created_at ? rep.created_at.slice(0, 10) : ''}</span>
                    <button onclick="promptUpdateRepair(${rep.id})" class="px-2.5 py-1 bg-white hover:bg-slate-50 text-blue-700 font-bold rounded-lg border border-slate-300 shadow-sm">
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
    formData.append("remarks", "Updated via Municipal Dispatch Command");

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
// 10. MANUAL VERIFICATION PORTAL
// ==========================================
async function loadUnverifiedDefects() {
    const tbody = document.getElementById("verification-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-slate-400">Loading unverified detections...</td></tr>`;

    try {
        const res = await fetch("/api/defects?limit=50");
        const data = await res.json();
        tbody.innerHTML = "";

        const unverified = data.defects.filter(d => d.verification_status === "Unverified");
        if (unverified.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-6 text-emerald-700 font-bold">All defect detections have been audited & verified!</td></tr>`;
            return;
        }

        unverified.forEach(d => {
            const row = document.createElement("tr");
            row.className = "border-b border-slate-100 text-xs hover:bg-slate-50";
            row.innerHTML = `
                <td class="py-3 px-4 font-mono font-bold text-blue-700">${d.track_id}</td>
                <td class="py-3 px-4 font-bold text-slate-800">${d.class_name} (${d.category_code})</td>
                <td class="py-3 px-4 font-bold ${d.severity === 'Severe' ? 'text-rose-700' : (d.severity === 'Moderate' ? 'text-amber-700' : 'text-emerald-700')}">${d.severity}</td>
                <td class="py-3 px-4 font-bold text-slate-800">${(d.confidence * 100).toFixed(0)}%</td>
                <td class="py-3 px-4 text-slate-500 font-mono">${d.latitude ? `${d.latitude}, ${d.longitude}` : 'No GPS'}</td>
                <td class="py-3 px-4 text-right space-x-2">
                    <button onclick="submitDefectVerification(${d.id}, 'Verified')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg shadow-sm">
                        Approve
                    </button>
                    <button onclick="submitDefectVerification(${d.id}, 'Rejected')" class="px-3 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold rounded-lg border border-rose-200">
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
    formData.append("reviewer", "Er. Rajesh Verma (Chief Municipal Engineer)");

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
// 11. MODEL BENCHMARK METRICS
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
            row.className = "border-b border-slate-100 text-xs hover:bg-slate-50";
            row.innerHTML = `
                <td class="py-3 px-4 font-bold text-slate-900">${mname}</td>
                <td class="py-3 px-4 font-mono text-slate-500">${mdata.model_file}</td>
                <td class="py-3 px-4 font-bold text-emerald-700">${(mdata.precision * 100).toFixed(1)}%</td>
                <td class="py-3 px-4 font-bold text-blue-700">${(mdata.recall * 100).toFixed(1)}%</td>
                <td class="py-3 px-4 font-bold text-slate-900">${mdata.f1_score.toFixed(4)}</td>
                <td class="py-3 px-4 font-bold text-cyan-700">${mdata.map50.toFixed(4)}</td>
                <td class="py-3 px-4 text-slate-600 font-medium">${mdata.avg_latency_ms} ms (${mdata.fps} FPS)</td>
            `;
            tbody.appendChild(row);
        }
    } catch (e) {
        console.error(e);
    }
}
