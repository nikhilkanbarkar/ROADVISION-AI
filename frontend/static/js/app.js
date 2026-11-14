/**
 * ROADVISION AI - Central Application Controller (White Theme & RBAC Edition)
 * Handles role-based dual-sided access (Citizen End vs Authority End),
 * AI image & video inspections, persistent ByteTrack tracking,
 * citizen grievance reporting, duplicate resolution, and municipal reporting.
 */

let categoryChart = null;
let severityChart = null;
let activeInspectionId = null;
let routeLocations = Object.create(null);

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
    updateMapKeyStatus();
    setupDropzone();
    setupVideoDropzone();
    setupCitizenDropzone();
    loadInspectionLocations();
});

async function loadInspectionLocations() {
    const selectors = ["citizen-road-name", "img-road-name", "vid-road-name"]
        .map(id => document.getElementById(id))
        .filter(Boolean);

    try {
        const response = await fetch("/api/inspection/locations");
        if (!response.ok) {
            throw new Error(`Location service returned HTTP ${response.status}`);
        }
        const data = await response.json();
        if (data.status !== "success" || !Array.isArray(data.locations) || data.locations.length === 0) {
            throw new Error("Location service returned no Belagavi locations");
        }
        populateNavigationLocations(data.locations);

        selectors.forEach(select => {
            const corridorGroup = document.createElement("optgroup");
            corridorGroup.label = "OSM Road Corridors";

            data.locations.forEach(location => {
                const option = document.createElement("option");
                option.value = location.id;
                option.textContent = location.name;
                option.dataset.locationName = location.name;
                option.dataset.latitude = location.latitude;
                option.dataset.longitude = location.longitude;
                if (location.road_type) option.dataset.roadType = location.road_type;
                if (location.speed_limit) option.dataset.speedLimit = location.speed_limit;
                corridorGroup.appendChild(option);
            });

            select.replaceChildren(corridorGroup);
            select.value = data.locations[0].id;
            if (!select.value && select.options.length > 0) select.selectedIndex = 0;
            select.disabled = false;
            select.addEventListener("change", () => applyInspectionLocation(select.id));
            applyInspectionLocation(select.id);
        });
    } catch (error) {
        console.error("Unable to load Belagavi inspection locations:", error);
        selectors.forEach(select => {
            select.replaceChildren(new Option("Belagavi locations unavailable — refresh to retry", ""));
            select.disabled = true;
        });
        ["nav-origin-select", "nav-dest-select"].forEach(id => {
            const select = document.getElementById(id);
            if (select) {
                select.replaceChildren(new Option("OSM road locations unavailable", ""));
                select.disabled = true;
            }
        });
    }
}

function populateNavigationLocations(locations) {
    const originSelect = document.getElementById("nav-origin-select");
    const destinationSelect = document.getElementById("nav-dest-select");
    if (!originSelect || !destinationSelect) return;

    routeLocations = Object.create(null);
    locations.forEach(location => {
        routeLocations[location.id] = {
            id: location.id,
            name: location.name,
            lat: Number(location.latitude),
            lon: Number(location.longitude)
        };
    });

    const populate = select => {
        const group = document.createElement("optgroup");
        group.label = "OSM Road Locations";
        locations.forEach(location => {
            const option = new Option(location.name, location.id);
            group.appendChild(option);
        });
        select.replaceChildren(group);
        select.disabled = locations.length < 2;
    };
    populate(originSelect);
    populate(destinationSelect);

    const origin = locations[0];
    const destination = locations[locations.length - 1];
    originSelect.value = origin.id;
    destinationSelect.value = destination.id;
    populateRoutePresets(locations);
}

function populateRoutePresets(locations) {
    const container = document.getElementById("route-presets");
    if (!container) return;
    container.replaceChildren();
    if (locations.length < 2) return;

    const pairs = [
        [locations[0], locations[locations.length - 1]],
        [locations[Math.floor(locations.length / 4)], locations[Math.floor(locations.length * 3 / 4)]]
    ];
    pairs.forEach(([origin, destination]) => {
        if (!origin || !destination || origin.id === destination.id) return;
        const button = document.createElement("button");
        button.type = "button";
        button.className = "px-2.5 py-1.5 text-left text-xs bg-slate-50 hover:bg-blue-50 hover:text-blue-700 rounded-lg border border-slate-200 transition font-medium truncate";
        button.textContent = `${origin.name} → ${destination.name}`;
        button.title = button.textContent;
        button.addEventListener("click", () => setRoutePreset(origin.id, destination.id));
        container.appendChild(button);
    });
}

function getSelectedInspectionLocation(selectId) {
    const select = document.getElementById(selectId);
    const option = select && select.options[select.selectedIndex];
    if (!option || !option.value) return null;

    return {
        name: option.dataset.locationName || option.textContent,
        latitude: Number(option.dataset.latitude),
        longitude: Number(option.dataset.longitude),
        roadType: option.dataset.roadType,
        speedLimit: option.dataset.speedLimit
    };
}

function applyInspectionLocation(selectId) {
    const location = getSelectedInspectionLocation(selectId);
    if (!location) return;

    if (selectId === "citizen-road-name") {
        const coordinates = document.getElementById("citizen-coords");
        if (coordinates) coordinates.value = `${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
    }

    const metadataFields = {
        "citizen-road-name": { roadType: "citizen-road-type", speedLimit: "citizen-speed" },
        "img-road-name": { roadType: "img-road-type", speedLimit: "img-speed-limit" },
        "vid-road-name": { roadType: "vid-road-type", speedLimit: "vid-speed-limit" }
    };
    const fields = metadataFields[selectId];
    if (fields && location.roadType) {
        const roadType = document.getElementById(fields.roadType);
        if (roadType && Array.from(roadType.options).some(option => option.value === location.roadType)) {
            roadType.value = location.roadType;
        }
    }
    if (fields && location.speedLimit) {
        const speedLimit = document.getElementById(fields.speedLimit);
        if (speedLimit) speedLimit.value = location.speedLimit;
    }
}

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

        switchTab("authority-citizen-reports");
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
    } else if (tabId === "citizen-navigate") {
        setTimeout(initRouteNavMap, 150);
    } else if (tabId === "citizen-myreports") {
        loadCitizenReports();
    } else if (tabId === "authority-citizen-reports") {
        loadAuthorityCitizenReports(currentAuthorityFilter || 'pending');
    } else if (tabId === "road-table") {
        loadRoadConditionTable();
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
                alert("GPS permission denied or unavailable. Using default Belagavi City Center coordinates.");
                document.getElementById("citizen-coords").value = "15.8497, 74.4977";
            }
        );
    } else {
        document.getElementById("citizen-coords").value = "15.8497, 74.4977";
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

    const selectedLocation = getSelectedInspectionLocation("citizen-road-name");
    if (!selectedLocation) {
        alert("Select a Belagavi location before submitting the report.");
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="send" class="w-4 h-4"></i><span>Submit Grievance to Authority</span>`;
        if (window.lucide) lucide.createIcons();
        return;
    }
    const roadName = selectedLocation.name;
    const roadType = document.getElementById("citizen-road-type") ? document.getElementById("citizen-road-type").value : "Arterial";
    const speed = document.getElementById("citizen-speed").value || "60";
    const coordsStr = document.getElementById("citizen-coords").value || "15.8497, 74.4977";
    const [lat, lon] = coordsStr.split(",").map(s => parseFloat(s.trim()));

    const formData = new FormData();
    formData.append("file", file);
    formData.append("road_name", roadName);
    formData.append("location_name", roadName);
    formData.append("road_type", roadType);
    formData.append("speed_limit", speed);
    formData.append("citizen_name", currentUser.name || "Priya Sharma");
    if (!isNaN(lat) && !isNaN(lon)) {
        formData.append("manual_lat", lat);
        formData.append("manual_lon", lon);
    }

    try {
        const res = await fetch("/api/citizen/report", { method: "POST", body: formData });
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

    document.getElementById("citizen-ticket-number").textContent = `#${data.ticket_code || data.code || "CITIZEN-REPORT"}`;
    const imgElem = document.getElementById("citizen-annotated-img");
    const videoElem = document.getElementById("citizen-annotated-video");
    const mediaUrl = data.media_type === "video"
        ? (data.annotated_video_url || data.annotated_url)
        : (data.annotated_url || data.original_url || "");
    if (data.media_type === "video") {
        imgElem.classList.add("hidden");
        imgElem.removeAttribute("src");
        videoElem.src = mediaUrl;
        videoElem.classList.remove("hidden");
        videoElem.load();
    } else {
        videoElem.pause();
        videoElem.removeAttribute("src");
        videoElem.classList.add("hidden");
        imgElem.src = mediaUrl;
        imgElem.classList.remove("hidden");
    }

    // Potholes count, condition %, damage count, overall health
    const potholes = Number(data.potholes_count || 0);
    const condPct = Number(data.condition_percentage ?? 100);
    const totalDef = Number(data.total_defects ?? data.unique_defects_count ?? potholes);
    const riskClass = String(data.risk_classification || "SAFE").toUpperCase();
    const riskScore = Number(data.risk_score || 0);
    const riskLevel = data.risk_level || "Low";

    const condElem = document.getElementById("citizen-condition-pct");
    if (condElem) condElem.textContent = `${condPct}%`;

    const potElem = document.getElementById("citizen-potholes-count");
    if (potElem) potElem.textContent = potholes;

    const damElem = document.getElementById("citizen-damage-count");
    if (damElem) damElem.textContent = totalDef;

    const scoreElem = document.getElementById("citizen-risk-score");
    if (scoreElem) scoreElem.textContent = `${riskScore.toFixed(1)} / 100`;
    const levelElem = document.getElementById("citizen-risk-level");
    if (levelElem) levelElem.textContent = `${riskLevel} exposure`;

    const healthElem = document.getElementById("citizen-overall-health");
    if (healthElem) {
        if (riskClass === "SAFE") {
            healthElem.textContent = "Safe / Sound";
            healthElem.className = "text-sm font-bold text-emerald-600 mt-1 block";
        } else if (riskClass === "MODERATE") {
            healthElem.textContent = "Fair / Noticeable Damage";
            healthElem.className = "text-sm font-bold text-amber-600 mt-1 block";
        } else {
            healthElem.textContent = "Poor / Severe Distress";
            healthElem.className = "text-sm font-bold text-rose-600 mt-1 block";
        }
    }

    const badgeElem = document.getElementById("citizen-risk-badge");
    if (badgeElem) {
        if (riskClass === "SAFE") {
            badgeElem.className = "px-3 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-800 border border-emerald-300 inline-block mt-0.5";
            badgeElem.textContent = "SAFE (GREEN)";
        } else if (riskClass === "MODERATE") {
            badgeElem.className = "px-3 py-1 rounded-full text-xs font-black bg-amber-100 text-amber-800 border border-amber-300 inline-block mt-0.5";
            badgeElem.textContent = "MODERATE (YELLOW)";
        } else {
            badgeElem.className = "px-3 py-1 rounded-full text-xs font-black bg-rose-100 text-rose-800 border border-rose-300 inline-block mt-0.5";
            badgeElem.textContent = "CRITICAL / RISKY (RED)";
        }
    }

    const alertBox = document.getElementById("citizen-risk-alert-box");
    const headline = document.getElementById("citizen-risk-headline");
    const desc = document.getElementById("citizen-risk-desc");
    const otherDefects = Math.max(0, totalDef - potholes);
    const measuredSummary = `${potholes} pothole(s) and ${otherDefects} other defect(s) detected across ${totalDef} unique defect(s). Road condition: ${condPct}%. Risk exposure: ${riskScore.toFixed(1)}/100 (${riskLevel}).`;

    if (riskClass === "SAFE") {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-emerald-50 border-emerald-200 text-emerald-900";
        headline.textContent = totalDef === 0 ? "Road Condition: Healthy — No Defects Detected" : "Road Condition: Generally Healthy — Low Damage";
        desc.textContent = `${measuredSummary} This survey indicates a healthy road condition. The report is pending authority verification.`;
    } else if (riskClass === "MODERATE") {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-amber-50 border-amber-200 text-amber-900";
        headline.textContent = `Moderate Road Damage — ${potholes} Pothole(s)`;
        desc.textContent = `${measuredSummary} Some maintenance may be needed. The report is pending authority verification.`;
    } else {
        alertBox.className = "p-4 rounded-xl border flex items-start space-x-3 bg-rose-50 border-rose-200 text-rose-900";
        headline.textContent = `High Road Risk — ${potholes} Pothole(s) Detected`;
        desc.textContent = `${measuredSummary} This distress level warrants prompt inspection. The report is pending authority verification.`;
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
            const evidencePreview = rep.annotated_url
                ? (rep.media_type === "video"
                    ? `<video src="${rep.annotated_url}" controls playsinline class="w-full max-h-72 rounded-lg bg-black" aria-label="Annotated road report video"></video>`
                    : `<img src="${rep.annotated_url}" class="w-full max-h-72 object-contain rounded-lg bg-slate-100" alt="Annotated road report" />`)
                : "";

            let statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">⏳ Pending Verification</span>`;
            if (rep.status === "Accepted" || rep.status === "ACCEPTED" || rep.verification_status === "VERIFIED" || rep.verification_status === "ACCEPTED") {
                statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">✓ Accepted & Verified</span>`;
            } else if (rep.status === "Rejected" || rep.status === "REJECTED" || rep.verification_status === "REJECTED") {
                statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-300">✕ Rejected</span>`;
            }

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
                        ${statusBadge}
                    </div>
                </div>

                ${evidencePreview}

                <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
                    <div>
                        <span class="text-slate-500 font-bold block">Observed Distress:</span>
                        <div class="font-semibold text-slate-800 mt-0.5">${rep.potholes_count || 0} pothole(s), ${Math.max(0, (rep.defect_count || 0) - (rep.potholes_count || 0))} other (${rep.severity})</div>
                    </div>
                    <div>
                        <span class="text-slate-500 font-bold block">Road Condition %:</span>
                        <div class="font-black text-blue-600 mt-0.5">${rep.condition_percentage !== undefined ? rep.condition_percentage : (100 - rep.risk_score)}%</div>
                    </div>
                    <div>
                        <span class="text-slate-500 font-bold block">Risk Classification & Exposure:</span>
                        <div class="font-bold text-amber-700 mt-0.5">${rep.risk_classification} · ${rep.risk_score}/100 (${rep.risk_level})</div>
                    </div>
                    <div>
                        <span class="text-slate-500 font-bold block">Authority Action:</span>
                        <div class="text-slate-600 mt-0.5 truncate">${rep.remarks || 'Pending municipal evaluation'}</div>
                    </div>
                </div>

                <!-- Progress Bar -->
                <div>
                    <div class="flex justify-between text-[11px] font-bold text-slate-600 mb-1">
                        <span>Municipal Resolution Progress</span>
                        <span>${rep.progress_pct}%</span>
                    </div>
                    <div class="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
                        <div class="h-full rounded-full transition-all duration-500 ${rep.progress_pct >= 100 ? 'bg-emerald-600' : (rep.progress_pct <= 20 ? 'bg-amber-500' : 'bg-blue-600')}" style="width: ${rep.progress_pct}%"></div>
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
    const selectedLocation = getSelectedInspectionLocation("img-road-name");
    if (!selectedLocation) {
        alert("Select a Belagavi location before starting the inspection.");
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="zap" class="w-4 h-4"></i><span>Start AI Damage Detection</span>`;
        if (window.lucide) lucide.createIcons();
        return;
    }
    formData.append("road_name", selectedLocation.name);
    formData.append("road_type", document.getElementById("img-road-type").value || "Arterial");
    formData.append("speed_limit", document.getElementById("img-speed-limit").value || "60");
    formData.append("manual_lat", selectedLocation.latitude);
    formData.append("manual_lon", selectedLocation.longitude);
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
    const selectedLocation = getSelectedInspectionLocation("vid-road-name");
    if (!selectedLocation) {
        alert("Select a Belagavi location before processing the video.");
        btn.disabled = false;
        progressContainer.classList.add("hidden");
        return;
    }
    formData.append("road_name", selectedLocation.name);
    formData.append("road_type", document.getElementById("vid-road-type").value || "Arterial");
    formData.append("speed_limit", document.getElementById("vid-speed-limit").value || "60");
    formData.append("manual_lat", selectedLocation.latitude);
    formData.append("manual_lon", selectedLocation.longitude);
    formData.append("weather", document.getElementById("vid-weather").value || "Clear/Dry");
    formData.append("conf_thresh", document.getElementById("vid-conf-thresh").value || "0.15");
    formData.append("stride", strideVal);
    formData.append("submitter_type", "authority");
    formData.append("submitter_name", currentUser.name || "Er. Rajesh Verma");

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

    const potholes = data.potholes_count !== undefined ? data.potholes_count : data.unique_defects_count;
    const condPct = data.condition_percentage !== undefined ? data.condition_percentage : (100 - (data.risk_score || 0));
    const riskClass = (data.risk_classification || (data.risk_score >= 50 ? "RISKY" : (data.risk_score >= 25 ? "MODERATE" : "SAFE"))).toUpperCase();

    const potEl = document.getElementById("vid-potholes-count");
    if (potEl) potEl.textContent = potholes;

    const unqEl = document.getElementById("vid-unique-defects");
    if (unqEl) unqEl.textContent = data.unique_defects_count || data.total_damage_count || potholes;

    const condEl = document.getElementById("vid-condition-pct");
    if (condEl) condEl.textContent = `${condPct}%`;

    const badgeEl = document.getElementById("vid-risk-badge");
    if (badgeEl) {
        if (riskClass === "SAFE") {
            badgeEl.className = "px-2 py-0.5 rounded text-xs font-black bg-emerald-100 text-emerald-800 border border-emerald-300 inline-block mt-1";
            badgeEl.textContent = "SAFE";
        } else if (riskClass === "MODERATE") {
            badgeEl.className = "px-2 py-0.5 rounded text-xs font-black bg-amber-100 text-amber-800 border border-amber-300 inline-block mt-1";
            badgeEl.textContent = "MODERATE";
        } else {
            badgeEl.className = "px-2 py-0.5 rounded text-xs font-black bg-rose-100 text-rose-800 border border-rose-300 inline-block mt-1";
            badgeEl.textContent = "RISKY";
        }
    }

    // Refresh official databases, map, table and dashboard
    loadDashboardAnalytics();
    loadRoadConditionTable();
    if (roadMap) loadMapPoints();

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
// 8. DUPLICATE DAMAGE DETECTION & AUTHORITY RESOLUTION
// ==========================================
async function loadDuplicates() {
    const container = document.getElementById("duplicates-container");
    if (!container) return;
    container.innerHTML = `<div class="p-8 text-center text-slate-400 font-medium">Scanning for cross-inspection duplicates...</div>`;

    try {
        const res = await fetch("/api/duplicates");
        const data = await res.json();
        container.innerHTML = "";

        if (!data.duplicates || data.duplicates.length === 0) {
            container.innerHTML = `
                <div class="glass-card p-8 text-center bg-white border border-slate-200">
                    <div class="text-emerald-700 font-extrabold text-lg mb-1">No Duplicate Candidates Pending Review</div>
                    <div class="text-sm text-slate-500">All submitted inspections and physical road damage records in Belagavi are consolidated and unique.</div>
                </div>
            `;
            return;
        }

        data.duplicates.forEach(dup => {
            const card = document.createElement("div");
            const isConfirmed = dup.decision_status === "Confirmed_Duplicate";
            const isAmbiguous = dup.decision_status === "Needs_Verification";
            const borderCol = isConfirmed ? "border-amber-500" : (isAmbiguous ? "border-cyan-500" : "border-slate-300");
            const badgeBg = isConfirmed ? "bg-amber-100 text-amber-900 border-amber-300" : (isAmbiguous ? "bg-cyan-100 text-cyan-900 border-cyan-300" : "bg-slate-100 text-slate-800 border-slate-300");
            const badgeText = isConfirmed ? "Confirmed Duplicate" : (isAmbiguous ? "Needs Verification (Ambiguous)" : dup.decision_status);

            const candPhoto = dup.candidate?.photo_url || "/static/img/placeholder_road.jpg";
            const existPhoto = dup.existing_damage?.photo_url || "/static/img/placeholder_road.jpg";

            card.className = `glass-card p-5 mb-5 border-l-4 ${borderCol} bg-white shadow-sm rounded-xl`;
            card.innerHTML = `
                <!-- Header / Status Banner -->
                <div class="flex flex-wrap justify-between items-center gap-2 mb-4 pb-3 border-b border-slate-100">
                    <div class="flex items-center space-x-2">
                        <span class="px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border ${badgeBg}">
                            ${badgeText}
                        </span>
                        <span class="text-xs text-slate-500 font-bold">Match ID #${dup.match_id}</span>
                    </div>
                    <div class="flex items-center space-x-3 text-xs">
                        <span class="text-slate-500 font-semibold">Overall Match Score:</span>
                        <span class="text-lg font-black ${dup.overall_matching_score >= 0.75 ? 'text-amber-700' : 'text-cyan-700'}">
                            ${Math.round((dup.overall_matching_score || 0) * 100)}%
                        </span>
                    </div>
                </div>

                <!-- Multi-Signal Metrics Strip -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg mb-4 text-center border border-slate-200">
                    <div>
                        <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">GPS Distance</div>
                        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${dup.spatial_distance_m !== null ? dup.spatial_distance_m + ' m' : 'No GPS'}</div>
                    </div>
                    <div>
                        <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Perceptual Hash</div>
                        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${dup.visual_similarity_pct}%</div>
                    </div>
                    <div>
                        <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Deep Embedding</div>
                        <div class="text-sm font-extrabold text-slate-900 mt-0.5">${dup.embedding_similarity_pct}%</div>
                    </div>
                    <div>
                        <div class="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Category Match</div>
                        <div class="text-sm font-extrabold ${dup.category_match ? 'text-emerald-700' : 'text-rose-700'} mt-0.5">
                            ${dup.category_match ? 'Matching' : 'Incompatible'}
                        </div>
                    </div>
                </div>

                <!-- Side-by-Side Photos & Evidence Comparison -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                    <!-- Left: Newly Submitted Report -->
                    <div class="border border-slate-200 rounded-lg p-3 bg-white">
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-xs font-black text-cyan-800 uppercase tracking-wider">New Submission</span>
                            <span class="text-[11px] font-bold text-slate-500">${dup.candidate?.submitter_type || 'Citizen'}</span>
                        </div>
                        <div class="h-44 bg-slate-100 rounded-md overflow-hidden mb-2 relative flex items-center justify-center">
                            <img src="${candPhoto}" alt="Candidate Report Photo" class="w-full h-full object-cover" onerror="this.src='/static/img/placeholder_road.jpg'" />
                        </div>
                        <div class="text-xs space-y-1">
                            <div class="font-bold text-slate-800 truncate">${dup.candidate?.road_name || 'Belagavi Road'}</div>
                            <div class="text-slate-600 flex justify-between">
                                <span>Code: <b class="font-mono">${dup.candidate?.code || 'N/A'}</b></span>
                                <span>Severity: <b class="text-amber-800">${dup.candidate?.severity || 'Moderate'}</b></span>
                            </div>
                        </div>
                    </div>

                    <!-- Right: Existing Physical Damage Asset -->
                    <div class="border border-slate-200 rounded-lg p-3 bg-white">
                        <div class="flex justify-between items-center mb-2">
                            <span class="text-xs font-black text-amber-800 uppercase tracking-wider">Existing Physical Asset</span>
                            <span class="text-[11px] font-bold text-emerald-700">Observed ${dup.existing_damage?.times_observed || 1}x</span>
                        </div>
                        <div class="h-44 bg-slate-100 rounded-md overflow-hidden mb-2 relative flex items-center justify-center">
                            <img src="${existPhoto}" alt="Existing Physical Defect Photo" class="w-full h-full object-cover" onerror="this.src='/static/img/placeholder_road.jpg'" />
                        </div>
                        <div class="text-xs space-y-1">
                            <div class="font-bold text-slate-800 truncate">${dup.existing_damage?.road_name || 'Corridor Asset'}</div>
                            <div class="text-slate-600 flex justify-between">
                                <span>Asset: <b class="font-mono text-emerald-800">${dup.existing_damage?.damage_code || 'N/A'}</b></span>
                                <span>Type: <b>${dup.existing_damage?.damage_type || 'Pothole'}</b></span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Explainable Decision Reason -->
                <div class="bg-amber-50/70 border border-amber-200/80 rounded-lg p-3 mb-4 text-xs text-amber-950">
                    <span class="font-bold">AI Duplicate Engine Analysis:</span>
                    <p class="mt-0.5 leading-relaxed text-slate-700">${dup.decision_reason}</p>
                </div>

                <!-- 3 Clear Authority Actions -->
                <div class="flex flex-wrap justify-end gap-2 pt-2 border-t border-slate-100">
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'REJECT_REPORT')" class="px-3.5 py-2 bg-white hover:bg-rose-50 text-xs font-bold text-rose-700 rounded-lg border border-rose-300 shadow-sm transition">
                        Reject Report
                    </button>
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'MARK_SEPARATE')" class="px-3.5 py-2 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 rounded-lg border border-slate-300 shadow-sm transition">
                        Mark as Separate Damage
                    </button>
                    <button onclick="resolveDuplicateMatch(${dup.match_id}, 'CONFIRM_DUPLICATE')" class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-xs font-bold text-white rounded-lg shadow-sm transition">
                        Confirm Duplicate (Link to Physical Damage)
                    </button>
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error loading duplicates:", e);
        container.innerHTML = `<div class="p-4 bg-rose-50 text-rose-700 text-xs rounded-lg">Failed to load duplicate candidates: ${e.message}</div>`;
    }
}

async function resolveDuplicateMatch(matchId, action) {
    try {
        const formData = new FormData();
        formData.append("action", action);
        formData.append("reviewer", "Er. Rajesh Verma (PWD Belagavi)");
        const res = await fetch(`/api/duplicates/${matchId}/resolve`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            loadDuplicates();
            // Refresh physical damage records and overview if available
            if (typeof loadRoadConditionsTable === "function") loadRoadConditionsTable();
            if (typeof loadDashboardAnalytics === "function") loadDashboardAnalytics();
        } else {
            alert(data.detail || "Failed to resolve duplicate match.");
        }
    } catch (e) {
        console.error(e);
        alert("Network error resolving duplicate: " + e.message);
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


// ==========================================
// 12. BELAGAVI RISK-AWARE MULTI-PATH ROUTE NAVIGATION
// ==========================================
let routeNavMap = null;
let routeNavLayerGroup = null;
let currentRouteData = null;
let activeRoutePolylines = {};
let activeDefectMarkers = [];
let clickPickMode = "origin"; // Toggles between origin and dest on map click

function initRouteNavMap() {
    if (routeNavMap) {
        setTimeout(() => routeNavMap.invalidateSize(), 150);
        return;
    }
    const container = document.getElementById("route-nav-map");
    if (!container) return;

    routeNavMap = L.map('route-nav-map', {
        zoomControl: true
    }).setView([15.8497, 74.4977], 13);

    createMapTileLayer().addTo(routeNavMap);
    routeNavLayerGroup = L.layerGroup().addTo(routeNavMap);

    // Interactive Map Click: Pick Origin or Destination directly on Belagavi map
    routeNavMap.on("click", (e) => {
        const clickedLat = e.latlng.lat;
        const clickedLon = e.latlng.lng;
        const location = {
            id: `map:${clickPickMode}`,
            name: `Map point ${clickedLat.toFixed(5)}, ${clickedLon.toFixed(5)}`,
            lat: clickedLat,
            lon: clickedLon
        };
        routeLocations[location.id] = location;
        const select = document.getElementById(
            clickPickMode === "origin" ? "nav-origin-select" : "nav-dest-select"
        );
        if (select) {
            const previousMapOption = select.querySelector('option[data-map-point="true"]');
            if (previousMapOption) previousMapOption.remove();
            const option = new Option(`${location.name} (OSRM will snap to road)`, location.id);
            option.dataset.mapPoint = "true";
            select.add(option);
            select.value = location.id;
        }

        if (clickPickMode === "origin") {
            clickPickMode = "destination";
            showRouteToast(`Origin selected at ${location.name}. Click the map for a destination.`);
        } else {
            clickPickMode = "origin";
            showRouteToast(`Destination selected at ${location.name}. Calculating OSRM routes...`);
            calculateSafeRoute();
        }
    });
}

function showRouteToast(msg) {
    const pill = document.getElementById("route-active-filter-pill");
    if (pill) {
        pill.textContent = msg;
        pill.className = "px-2.5 py-1 rounded font-bold text-[11px] bg-blue-50 text-blue-800 border border-blue-200 transition";
    }
}

function setRoutePreset(origKey, destKey) {
    const oSel = document.getElementById("nav-origin-select");
    const dSel = document.getElementById("nav-dest-select");
    if (!routeLocations[origKey] || !routeLocations[destKey]) return;
    if (oSel) oSel.value = origKey;
    if (dSel) dSel.value = destKey;
    calculateSafeRoute();
}

async function calculateSafeRoute() {
    const originSelect = document.getElementById("nav-origin-select");
    const destinationSelect = document.getElementById("nav-dest-select");
    if (!originSelect || !destinationSelect) return;
    const orig = routeLocations[originSelect.value];
    const dest = routeLocations[destinationSelect.value];

    if (!orig || !dest) {
        alert("Select road locations loaded from the OSM road catalog.");
        return;
    }
    if (orig.id === dest.id || (Math.abs(orig.lat - dest.lat) < 0.00001 && Math.abs(orig.lon - dest.lon) < 0.00001)) {
        alert("Please select distinct origin and destination road locations.");
        return;
    }

    const btn = document.getElementById("btn-calc-route");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<span class="animate-spin inline-block mr-2">&#9696;</span> Requesting real OSRM road routes...`;
    }

    const formData = new FormData();
    formData.append("origin_lat", orig.lat);
    formData.append("origin_lon", orig.lon);
    formData.append("dest_lat", dest.lat);
    formData.append("dest_lon", dest.lon);

    try {
        const res = await fetch("/api/routes/navigate", {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok && data.status === "success") {
            currentRouteData = data;
            displayRouteRecommendationResults(data);
        } else {
            alert("Routing notice: " + (data.detail || data.message || "OSRM could not find a road route."));
        }
    } catch(e) {
        console.error("Navigation error:", e);
        alert("Failed to contact OSRM. Check the routing service connection and retry.");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i data-lucide="navigation" class="w-4 h-4"></i><span>Calculate OSRM Routes & Risk</span>`;
            if (window.lucide) lucide.createIcons();
        }
    }
}

function displayRouteRecommendationResults(data) {
    const placeholder = document.getElementById("route-results-placeholder");
    if (placeholder) placeholder.classList.add("hidden");

    const container = document.getElementById("route-results-container");
    if (container) container.classList.remove("hidden");

    const recTitle = document.getElementById("route-recommendation-title");
    const compText = document.getElementById("route-comparison-text");
    if (recTitle) recTitle.textContent = "AI Road Damage Risk Evaluation & Route Selection";
    if (compText) {
        const routeCount = Number(data.route_count || (data.routes || []).length);
        const availableRoutes = `${routeCount} distinct OSRM route${routeCount === 1 ? "" : "s"} returned`;
        const scoring = data.scoring_method ? ` Scoring: ${data.scoring_method}.` : "";
        compText.textContent = `${data.comparison_summary || "Route risk assessment completed."} ${availableRoutes}.${scoring}`;
    }

    // Render Cards Grid
    const cardsGrid = document.getElementById("routes-cards-grid");
    if (cardsGrid) {
        cardsGrid.innerHTML = "";
        const routes = data.routes || [];

        routes.forEach((r, idx) => {
            const isRec = r.is_recommended || (r.route_id === 1);
            const card = document.createElement("div");
            card.id = `route-card-${r.route_id}`;
            card.className = `p-4 rounded-xl border transition-all cursor-pointer shadow-sm relative overflow-hidden ${
                isRec
                ? 'bg-emerald-50/70 border-emerald-300 ring-2 ring-emerald-500/20 hover:border-emerald-500'
                : 'bg-white border-slate-200 hover:border-slate-400 hover:shadow-md'
            } space-y-3`;

            // Color Indicator top stripe
            const colorStripe = `<div class="absolute top-0 left-0 right-0 h-1.5" style="background-color: ${r.color};"></div>`;

            let riskBadgeClass = "bg-emerald-100 text-emerald-800 border-emerald-300";
            if (r.risk_level === "Critical" || r.risk_level === "High") riskBadgeClass = "bg-rose-100 text-rose-800 border-rose-300";
            else if (r.risk_level === "Moderate") riskBadgeClass = "bg-amber-100 text-amber-800 border-amber-300";

            card.innerHTML = `
                ${colorStripe}
                <div class="flex items-center justify-between pt-1">
                    <span class="text-[11px] font-extrabold uppercase flex items-center space-x-1.5" style="color: ${r.color};">
                        <span class="w-2.5 h-2.5 rounded-full inline-block" style="background-color: ${r.color};"></span>
                        <span>${r.summary_badge || (isRec ? '⭐ Recommended route' : 'Alternative')}</span>
                    </span>
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${riskBadgeClass}">
                        ${r.risk_level} Risk (${r.exposure_score}/100)
                    </span>
                </div>

                <div class="text-sm font-extrabold text-slate-900 leading-snug">${r.name}</div>

                <div class="grid grid-cols-5 gap-1.5 text-center text-xs">
                    <div class="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                        <span class="text-[9px] text-slate-400 block uppercase font-bold">Distance</span>
                        <strong class="text-slate-800 font-black">${r.distance_km} km</strong>
                    </div>
                    <div class="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                        <span class="text-[9px] text-slate-400 block uppercase font-bold">Est. Time</span>
                        <strong class="text-slate-800 font-black">${r.estimated_time_min} m</strong>
                    </div>
                    <div class="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                        <span class="text-[9px] text-slate-400 block uppercase font-bold">Exposure</span>
                        <strong class="font-black" style="color: ${r.risk_color || r.color};">${r.exposure_score}</strong>
                    </div>
                    <div class="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                        <span class="text-[9px] text-slate-400 block uppercase font-bold">Score</span>
                        <strong class="text-slate-800 font-black">${r.recommendation_score}</strong>
                    </div>
                    <div class="bg-white p-2 rounded-lg border border-slate-200 shadow-2xs">
                        <span class="text-[9px] text-slate-400 block uppercase font-bold">Potholes</span>
                        <strong class="font-black ${r.potholes_count > 0 ? 'text-rose-600' : 'text-slate-700'}">${r.potholes_count}</strong>
                    </div>
                </div>

                <div class="text-[11px] text-slate-600 space-y-1 pt-1 border-t border-slate-200/60 leading-tight">
                    ${(r.factors || []).map(f => `<div class="flex items-start space-x-1.5"><span class="text-slate-400 shrink-0">&bull;</span><span>${f}</span></div>`).join('')}
                </div>

                <div class="pt-2 flex items-center justify-between">
                    <button type="button" onclick="focusRouteOnMap(${r.route_id})" class="w-full py-1.5 text-center rounded-lg text-xs font-bold transition shadow-sm border" style="background-color: ${isRec ? r.color : '#f8fafc'}; color: ${isRec ? '#ffffff' : r.color}; border-color: ${r.color};">
                        <span>${isRec ? 'Recommended Route' : 'Inspect Path on Map'}</span>
                    </button>
                </div>
            `;

            card.addEventListener("click", () => focusRouteOnMap(r.route_id));
            cardsGrid.appendChild(card);
        });
    }

    // Render road-following paths with colors tied to their calculated risk.
    initRouteNavMap();
    if (routeNavMap && routeNavLayerGroup) {
        routeNavLayerGroup.clearLayers();
        activeRoutePolylines = {};
        activeDefectMarkers = [];
        const allBounds = [];

        // Build dynamic route selector pills
        const pillsContainer = document.getElementById("route-map-pills");
        if (pillsContainer) {
            pillsContainer.innerHTML = `<button type="button" onclick="focusRouteOnMap('all')" class="px-2 py-1 rounded text-[11px] font-bold bg-white hover:bg-slate-50 border border-slate-300 text-slate-700">All Paths</button>`;
        }

        const routes = data.routes || [];

        // Draw alternatives first so the recommended path remains visible on top.
        const reverseRoutes = [...routes].reverse();

        reverseRoutes.forEach(r => {
            const isRec = r.is_recommended || (r.route_id === 1);
            const polyline = r.polyline || [];
            polyline.forEach(c => allBounds.push(c));
            const risk = String(r.risk_level || "").toLowerCase();
            const routeColor = r.risk_color || r.color || (
                risk === "critical" || risk === "high" ? "#dc2626" :
                    risk === "moderate" ? "#d97706" : "#059669"
            );

            const line = L.polyline(polyline, {
                color: routeColor,
                weight: isRec ? 8 : 5,
                opacity: isRec ? 0.98 : 0.82,
                dashArray: isRec ? null : "8 6",
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(routeNavLayerGroup);

            // Detailed Interactive Popup
            line.bindPopup(`
                <div class="p-2 space-y-1.5 min-w-[200px]">
                    <div class="flex items-center space-x-1.5 font-black text-xs" style="color: ${routeColor};">
                        <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${routeColor};"></span>
                        <span>${isRec ? 'Recommended' : 'Alternative'} · ${r.risk_level || 'Unknown'} risk</span>
                    </div>
                    <div class="text-[11px] text-slate-700">
                        <div><strong>Distance:</strong> ${r.distance_km} km | <strong>Time:</strong> ${r.estimated_time_min} min</div>
                        <div><strong>Road Distress Exposure:</strong> <span class="font-bold" style="color: ${routeColor};">${r.exposure_score}/100 (${r.risk_level})</span></div>
                        <div><strong>Severe Potholes:</strong> ${r.severe_defects} cavities</div>
                    </div>
                    <div class="text-[10px] text-slate-500 italic pt-1 border-t border-slate-200">
                        ${(r.factors || [])[0] || 'Belagavi Road Corridor'}
                    </div>
                </div>
            `);

            line.on("click", () => focusRouteOnMap(r.route_id));
            activeRoutePolylines[r.route_id] = line;

            // Add filter pill
            if (pillsContainer) {
                const pBtn = document.createElement("button");
                pBtn.type = "button";
                pBtn.className = "px-2 py-1 rounded text-[11px] font-bold border transition";
                pBtn.style.borderColor = routeColor;
                pBtn.style.color = routeColor;
                pBtn.style.backgroundColor = isRec ? '#ecfdf5' : '#ffffff';
                pBtn.textContent = `Route ${r.route_id} (${r.distance_km} km)`;
                pBtn.onclick = () => focusRouteOnMap(r.route_id);
                pillsContainer.appendChild(pBtn);
            }

            // Render Pothole and Distress Markers along this route
            (r.matched_defects || []).forEach(d => {
                const isSevere = (d.severity === "Severe");
                const mColor = isSevere ? "#dc2626" : (d.severity === "Moderate" ? "#ea580c" : "#10b981");

                const defMarker = L.circleMarker([d.lat, d.lon], {
                    radius: isSevere ? 8 : 6,
                    color: "#ffffff",
                    weight: 2,
                    fillColor: mColor,
                    fillOpacity: 0.95
                }).addTo(routeNavLayerGroup);

                defMarker.bindPopup(`
                    <div class="text-xs p-1">
                        <strong class="${isSevere ? 'text-rose-600' : 'text-amber-700'} font-black flex items-center space-x-1">
                            <span>⚠️ ${isSevere ? 'Severe Pothole Cavity' : 'Road Surface Defect'}</span>
                        </strong>
                        <div class="text-[11px] text-slate-700 mt-1">
                            <div>Category: <strong>${d.category_code || 'D40'}</strong> &bull; Severity: <strong>${d.severity}</strong></div>
                            <div>On: <strong>${r.name}</strong></div>
                            <div>GPS: <span class="font-mono text-[10px]">${d.lat.toFixed(4)}, ${d.lon.toFixed(4)}</span></div>
                        </div>
                    </div>
                `);

                activeDefectMarkers.push(defMarker);
            });
        });

        // Add Origin (Start) and Destination (End) Markers
        if (data.origin) {
            const mO = L.circleMarker([data.origin.lat, data.origin.lon], {
                radius: 10,
                color: '#ffffff',
                weight: 3,
                fillColor: '#059669',
                fillOpacity: 1.0
            }).addTo(routeNavLayerGroup);
            mO.bindPopup(`<b>🟢 Start Origin (A):</b><br>${data.origin.junction}`).openPopup();
        }

        if (data.destination) {
            const mD = L.circleMarker([data.destination.lat, data.destination.lon], {
                radius: 10,
                color: '#ffffff',
                weight: 3,
                fillColor: '#2563eb',
                fillOpacity: 1.0
            }).addTo(routeNavLayerGroup);
            mD.bindPopup(`<b>🏁 Destination (B):</b><br>${data.destination.junction}`);
        }

        if (allBounds.length > 0) {
            setTimeout(() => {
                routeNavMap.invalidateSize();
                routeNavMap.fitBounds(allBounds, { padding: [40, 40] });
            }, 100);
        }
    }

    if (window.lucide) lucide.createIcons();
}

function focusRouteOnMap(routeId) {
    if (!currentRouteData || !routeNavMap) return;

    const routes = currentRouteData.routes || [];
    const pill = document.getElementById("route-active-filter-pill");

    if (routeId === "all") {
        routes.forEach(r => {
            const line = activeRoutePolylines[r.route_id];
            if (line) {
                line.setStyle({ weight: (r.route_id === 1 ? 7 : 5), opacity: 0.85 });
            }
            const card = document.getElementById(`route-card-${r.route_id}`);
            if (card) card.classList.remove("ring-4", "ring-blue-400");
        });
        if (pill) pill.textContent = "Showing All Paths";
        return;
    }

    routes.forEach(r => {
        const line = activeRoutePolylines[r.route_id];
        const card = document.getElementById(`route-card-${r.route_id}`);

        if (r.route_id === routeId) {
            if (line) {
                line.bringToFront();
                line.setStyle({ weight: 9, opacity: 1.0 });
                line.openPopup();
                routeNavMap.fitBounds(line.getBounds(), { padding: [50, 50] });
            }
            if (card) card.classList.add("ring-4", "ring-blue-400");
            if (pill) pill.textContent = `Active: ${r.name} (${r.risk_level} Risk)`;
        } else {
            if (line) {
                line.setStyle({ weight: 4, opacity: 0.35 });
            }
            if (card) card.classList.remove("ring-4", "ring-blue-400");
        }
    });
}
// ==========================================
// 13. MAP API KEY SETTINGS (CARTO / OPENSTREETMAP)
// ==========================================
function saveMapApiKey() {
    const input = document.getElementById("setting-map-api-key");
    const key = (input && input.value) ? input.value.trim() : "";
    if (!key) {
        alert("Please enter a valid CARTO or basemap API key, or click 'Use Free OSM' to use OpenStreetMap.");
        return;
    }
    localStorage.setItem("roadvision_map_key", key);
    updateMapKeyStatus();
    alert("Map API Key saved successfully! The map tiles will now use your key.");
    location.reload();
}

function clearMapApiKey() {
    localStorage.removeItem("roadvision_map_key");
    const input = document.getElementById("setting-map-api-key");
    if (input) input.value = "";
    updateMapKeyStatus();
    alert("Map reset to 100% Free OpenStreetMap (No API key required).");
    location.reload();
}

function updateMapKeyStatus() {
    const statusEl = document.getElementById("map-key-status");
    const input = document.getElementById("setting-map-api-key");
    const savedKey = localStorage.getItem("roadvision_map_key") || "";
    if (savedKey) {
        if (input) input.value = savedKey;
        if (statusEl) {
            statusEl.className = "text-blue-700 font-bold text-[11px] mt-1 block";
            statusEl.textContent = `Active: Custom Basemap Key (${savedKey.substring(0, 6)}••••)`;
        }
    } else {
        if (input) input.value = "";
        if (statusEl) {
            statusEl.className = "text-emerald-700 font-bold text-[11px] mt-1 block";
            statusEl.textContent = "Active: OpenStreetMap (Free, No API Key Required)";
        }
    }
}


// ==========================================
// 4B. AUTHORITY CITIZEN REPORTS VERIFICATION (SECTION 4)
// ==========================================
let currentAuthorityFilter = "pending";

function filterAuthorityReports(status) {
    currentAuthorityFilter = status;
    const btnPending = document.getElementById("auth-rep-filter-pending");
    const btnAccepted = document.getElementById("auth-rep-filter-accepted");
    const btnRejected = document.getElementById("auth-rep-filter-rejected");
    const btnAll = document.getElementById("auth-rep-filter-all");

    [btnPending, btnAccepted, btnRejected, btnAll].forEach(btn => {
        if (!btn) return;
        btn.className = "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-white text-slate-600 hover:text-slate-900 border border-slate-200";
    });

    if (status === "pending" && btnPending) {
        btnPending.className = "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-amber-50 text-amber-800 border border-amber-300 shadow-sm";
    } else if (status === "accepted" && btnAccepted) {
        btnAccepted.className = "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-sm";
    } else if (status === "rejected" && btnRejected) {
        btnRejected.className = "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-rose-50 text-rose-800 border border-rose-300 shadow-sm";
    } else if (status === "all" && btnAll) {
        btnAll.className = "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center space-x-2 bg-blue-50 text-blue-700 border border-blue-300 shadow-sm";
    }

    loadAuthorityCitizenReports(status);
}

async function loadAuthorityCitizenReports(statusFilter = "pending") {
    const list = document.getElementById("authority-reports-list");
    if (!list) return;
    list.innerHTML = `<div class="text-center py-10 text-slate-400 font-medium"><span class="animate-spin inline-block mr-2">&#9696;</span> Fetching citizen reports...</div>`;

    try {
        const res = await fetch(`/api/authority/citizen-reports?status=${statusFilter}`);
        const data = await res.json();
        const reports = data.reports || [];

        // Update badge counts
        const bPend = document.getElementById("badge-count-pending");
        if (bPend && data.pending_count !== undefined) bPend.textContent = data.pending_count;

        const bAcc = document.getElementById("badge-count-accepted");
        if (bAcc && data.accepted_count !== undefined) bAcc.textContent = data.accepted_count;

        const bRej = document.getElementById("badge-count-rejected");
        if (bRej && data.rejected_count !== undefined) bRej.textContent = data.rejected_count;

        const navB = document.getElementById("nav-pending-reports-badge");
        if (navB && data.pending_count !== undefined) navB.textContent = data.pending_count;

        list.innerHTML = "";

        if (reports.length === 0) {
            list.innerHTML = `
                <div class="glass-card p-10 text-center bg-white border border-slate-200">
                    <div class="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-2">
                        <i data-lucide="inbox" class="w-6 h-6"></i>
                    </div>
                    <div class="text-slate-800 font-bold text-base">No ${statusFilter} Reports Found</div>
                    <div class="text-xs text-slate-500 mt-1">There are currently no citizen submissions matching this status.</div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        reports.forEach(rep => {
            const card = document.createElement("div");
            card.className = "glass-card p-6 bg-white border border-slate-200 shadow-sm rounded-2xl space-y-4";

            const isPending = (rep.status === "Pending" || rep.status === "Pending Verification");
            const isAccepted = (rep.status === "Accepted" || rep.status === "ACCEPTED");
            const isRejected = (rep.status === "Rejected" || rep.status === "REJECTED");

            let statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300">⏳ Awaiting Verification</span>`;
            if (isAccepted) {
                statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">✓ Accepted & Verified</span>`;
            } else if (isRejected) {
                statusBadge = `<span class="px-3 py-1 rounded-full text-xs font-bold bg-rose-100 text-rose-900 border border-rose-300">✕ Rejected</span>`;
            }

            const riskClass = (rep.risk_classification || (rep.risk_score >= 50 ? "RISKY" : (rep.risk_score >= 25 ? "MODERATE" : "SAFE"))).toUpperCase();
            let riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">SAFE (GREEN)</span>`;
            if (riskClass === "RISKY") {
                riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-black bg-rose-100 text-rose-800">RISKY (RED)</span>`;
            } else if (riskClass === "MODERATE") {
                riskBadge = `<span class="px-2.5 py-0.5 rounded-full text-xs font-black bg-amber-100 text-amber-800">MODERATE (YELLOW)</span>`;
            }

            // Media Preview: Video player if video, otherwise image
            let mediaPreview = "";
            if (rep.media_type === "video" || (rep.media_url && rep.media_url.match(/\.(mp4|webm|avi|mov)$/i))) {
                const annotatedVideoUrl = rep.annotated_video_url || rep.annotated_url;
                mediaPreview = annotatedVideoUrl
                    ? `
                        <div class="rounded-xl overflow-hidden bg-black aspect-video border border-slate-200 shadow-inner">
                            <video src="${annotatedVideoUrl}" controls playsinline class="w-full h-full object-contain" aria-label="AI annotated citizen report video with bounding boxes"></video>
                        </div>
                        <div class="text-[11px] text-emerald-700 font-semibold">AI-annotated video — detected damage is outlined.</div>
                    `
                    : `<div class="p-4 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-800">Annotated video is not available for this report.</div>`;
            } else if (rep.annotated_url || rep.media_url) {
                mediaPreview = `
                    <div class="rounded-xl overflow-hidden bg-slate-100 border border-slate-200">
                        <img src="${rep.annotated_url || rep.media_url}" class="w-full max-h-56 object-cover" alt="Defect Evidence" />
                    </div>
                `;
            }

            card.innerHTML = `
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-mono text-xs font-black text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">${rep.code}</span>
                            <span class="text-xs text-slate-500 font-medium">${rep.upload_time || 'Recent'}</span>
                            <span class="text-xs text-slate-600 font-semibold">&bull; Citizen: <strong>${rep.submitter_name || 'Public Motorist'}</strong></span>
                        </div>
                        <h3 class="text-lg font-bold text-slate-900 mt-1">${rep.road_name}</h3>
                        <div class="text-xs text-slate-500 flex items-center space-x-3 mt-0.5">
                            <span>Class: <strong>${rep.road_type}</strong></span>
                            <span>Speed Limit: <strong>${rep.speed_limit} km/h</strong></span>
                            <span>GPS: <strong class="font-mono">${rep.latitude ? `${rep.latitude.toFixed(4)}, ${rep.longitude.toFixed(4)}` : 'Belagavi'}</strong></span>
                        </div>
                    </div>
                    <div>
                        ${statusBadge}
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- Left: Media Evidence Preview -->
                    <div class="space-y-2">
                        <div class="text-xs font-bold text-slate-700 uppercase">Uploaded Evidence</div>
                        ${mediaPreview}
                    </div>

                    <!-- Middle: AI Inspection Results -->
                    <div class="space-y-3">
                        <div class="text-xs font-bold text-slate-700 uppercase">AI Inspection Analysis</div>
                        <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-3">
                            <div class="flex justify-between items-center text-xs">
                                <span class="text-slate-500 font-semibold">Detected Potholes:</span>
                                <strong class="text-sm font-black text-rose-600">${rep.potholes_count !== undefined ? rep.potholes_count : rep.unique_defects}</strong>
                            </div>
                            <div class="flex justify-between items-center text-xs">
                                <span class="text-slate-500 font-semibold">Road Condition Percentage:</span>
                                <strong class="text-sm font-black text-blue-600">${rep.condition_percentage !== undefined ? rep.condition_percentage : (100 - rep.risk_score)}%</strong>
                            </div>
                            <div class="flex justify-between items-center text-xs">
                                <span class="text-slate-500 font-semibold">Risk Classification:</span>
                                <div>${riskBadge}</div>
                            </div>
                            <div class="flex justify-between items-center text-xs pt-2 border-t border-slate-200">
                                <span class="text-slate-500 font-semibold">Risk Exposure:</span>
                                <strong class="text-slate-800">${rep.risk_score}/100 (${rep.risk_level})</strong>
                            </div>
                        </div>
                    </div>

                    <!-- Right: Verification Audit & Decision Actions -->
                    <div class="space-y-3 flex flex-col justify-between">
                        <div>
                            <div class="text-xs font-bold text-slate-700 uppercase mb-2">Authority Decision</div>
                            <p class="text-xs text-slate-600 leading-relaxed">
                                ${isPending
                                    ? 'Accepting verifies this report and immediately updates the official road condition database, GIS map, Multi-Route Risk Finder, and Condition Table.'
                                    : (isAccepted
                                        ? `Verified by <strong>${rep.verified_by || 'Authority'}</strong>. Official road condition updated.`
                                        : `Rejected by <strong>${rep.verified_by || 'Authority'}</strong>. Preserved for audit without modifying official road database.`)}
                            </p>
                        </div>

                        ${isPending ? `
                            <div class="space-y-2 pt-2">
                                <button onclick="verifyAuthorityReport(${rep.id}, 'ACCEPT')" class="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-md shadow-emerald-600/20 transition flex items-center justify-center space-x-2">
                                    <i data-lucide="check-circle" class="w-4 h-4"></i>
                                    <span>Accept Report & Update Official Database</span>
                                </button>
                                <button onclick="verifyAuthorityReport(${rep.id}, 'REJECT')" class="w-full py-2.5 px-4 bg-rose-50 hover:bg-rose-100 text-rose-700 font-bold text-xs rounded-xl border border-rose-200 transition flex items-center justify-center space-x-2">
                                    <i data-lucide="x-circle" class="w-4 h-4"></i>
                                    <span>Reject Report</span>
                                </button>
                            </div>
                        ` : (isAccepted ? `
                            <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-900 text-xs font-semibold flex items-center space-x-2">
                                <i data-lucide="check" class="w-4 h-4 text-emerald-600 shrink-0"></i>
                                <span>Report Officially Verified & Integrated</span>
                            </div>
                        ` : `
                            <div class="p-3 bg-rose-50 rounded-xl border border-rose-200 text-rose-900 text-xs font-semibold flex items-center space-x-2">
                                <i data-lucide="shield-x" class="w-4 h-4 text-rose-600 shrink-0"></i>
                                <span>Report Rejected (Audit Record Maintained)</span>
                            </div>
                        `)}
                    </div>
                </div>
            `;

            list.appendChild(card);
        });

        if (window.lucide) lucide.createIcons();
    } catch (e) {
        console.error("Error loading authority citizen reports:", e);
    }
}

async function verifyAuthorityReport(reportId, action) {
    const isAccept = (action === "ACCEPT");
    const confirmMsg = isAccept
        ? "Accept citizen report? This will update the official road condition database, GIS map, Multi-Route Risk Finder, and Condition Table."
        : "Reject this report? The report will be moved to Rejected status and will NOT alter official road data.";

    if (!confirm(confirmMsg)) return;

    try {
        const formData = new FormData();
        formData.append("action", action);
        formData.append("notes", isAccept ? "Officially accepted by Municipal Engineer" : "Rejected during manual inspection audit");

        const res = await fetch(`/api/authority/reports/${reportId}/verify`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (data.status === "success") {
            alert(isAccept
                ? "Report ACCEPTED! Official road database, GIS map, and condition table updated."
                : "Report REJECTED and moved to Rejected Reports.");
            loadAuthorityCitizenReports(currentAuthorityFilter);
            loadDashboardAnalytics();
            loadRoadConditionTable();
            if (roadMap) loadMapPoints();
        } else {
            alert("Verification error: " + (data.detail || "Unable to update report."));
        }
    } catch (e) {
        console.error("Error verifying citizen report:", e);
        alert("Failed to submit verification action.");
    }
}

// ==========================================
// 4C. ROAD CONDITION TABLE & HISTORY (SECTION 8)
// ==========================================
let roadTableSearchTimer = null;

function debounceRoadTableSearch() {
    clearTimeout(roadTableSearchTimer);
    roadTableSearchTimer = setTimeout(() => {
        loadRoadConditionTable();
    }, 300);
}

async function loadRoadConditionTable() {
    const tbody = document.getElementById("road-condition-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">Loading road condition records...</td></tr>`;

    const searchInput = document.getElementById("road-table-search");
    const query = searchInput ? searchInput.value.trim() : "";

    const riskSelect = document.getElementById("road-table-risk-filter");
    const risk = riskSelect ? riskSelect.value : "";

    try {
        const url = `/api/roads/condition?search=${encodeURIComponent(query)}&risk_level=${encodeURIComponent(risk)}`;
        const res = await fetch(url);
        const data = await res.json();
        const roads = data.roads || [];

        tbody.innerHTML = "";

        if (roads.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400">No roads matching criteria.</td></tr>`;
            return;
        }

        roads.forEach(road => {
            const riskClass = (road.risk_classification || "SAFE").toUpperCase();
            let riskBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-black bg-emerald-100 text-emerald-800 border border-emerald-300">SAFE</span>`;
            if (riskClass === "RISKY") {
                riskBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-black bg-rose-100 text-rose-800 border border-rose-300">RISKY</span>`;
            } else if (riskClass === "MODERATE") {
                riskBadge = `<span class="px-2.5 py-1 rounded-full text-xs font-black bg-amber-100 text-amber-800 border border-amber-300">MODERATE</span>`;
            }

            const condPct = road.condition_percentage;
            let barColor = condPct >= 80 ? "bg-emerald-600" : (condPct >= 50 ? "bg-amber-500" : "bg-rose-600");

            const row = document.createElement("tr");
            row.className = "hover:bg-slate-50 transition border-b border-slate-100";
            row.innerHTML = `
                <td class="py-3 px-4 font-bold text-slate-900">
                    <div>${road.name}</div>
                    <span class="text-[10px] font-semibold text-slate-400 uppercase">${road.segment_code} &bull; ${road.road_type} (${road.speed_limit} km/h)</span>
                </td>
                <td class="py-3 px-4 text-slate-600 font-medium">${road.location || 'Belagavi Corridor'}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-0.5 rounded-full text-xs font-black ${road.potholes_count > 0 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-600'}">
                        ${road.potholes_count}
                    </span>
                </td>
                <td class="py-3 px-4">
                    <div class="flex items-center space-x-2">
                        <strong class="font-black text-slate-800 text-xs w-12">${condPct}%</strong>
                        <div class="w-24 bg-slate-200 rounded-full h-2 overflow-hidden">
                            <div class="${barColor} h-full rounded-full" style="width: ${condPct}%;"></div>
                        </div>
                    </div>
                </td>
                <td class="py-3 px-4">${riskBadge}</td>
                <td class="py-3 px-4 text-slate-500 text-[11px]">
                    <div>${road.last_inspected_date || 'Recent'}</div>
                    <span class="text-[10px] text-slate-400">${road.inspection_source}</span>
                </td>
                <td class="py-3 px-4 text-right">
                    <button onclick="viewRoadHistory(${road.id}, '${road.name.replace(/'/g, "\'")}')" class="px-3 py-1 bg-white hover:bg-slate-100 text-xs font-bold text-indigo-700 rounded-lg border border-slate-300 shadow-sm">
                        View History
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (e) {
        console.error("Error loading road condition table:", e);
    }
}

async function viewRoadHistory(roadId, roadName) {
    try {
        const res = await fetch(`/api/roads/${roadId}/history`);
        const data = await res.json();

        document.getElementById("history-modal-road-name").textContent = `Road Inspection History: ${data.road_name}`;
        document.getElementById("history-modal-road-sub").textContent = `ID: BLG-${data.road_id} &bull; Monitored Road Corridor`;

        const cur = data.current_condition || {};
        document.getElementById("history-modal-condition").textContent = `${cur.condition_percentage || 0}%`;
        document.getElementById("history-modal-potholes").textContent = cur.potholes_count || 0;
        document.getElementById("history-modal-risk").textContent = cur.risk_classification || 'SAFE';
        document.getElementById("history-modal-count").textContent = data.total_inspections || 0;

        const tbody = document.getElementById("road-history-timeline-body");
        tbody.innerHTML = "";

        const history = data.history || [];
        if (history.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-slate-400">No inspection history recorded for this road yet.</td></tr>`;
        } else {
            history.forEach(h => {
                const row = document.createElement("tr");
                row.className = "border-b border-slate-100 text-xs hover:bg-slate-50";

                let rBadge = `<span class="px-2 py-0.5 rounded font-bold text-[10px] bg-emerald-100 text-emerald-800">SAFE</span>`;
                if (h.risk_classification === "RISKY") {
                    rBadge = `<span class="px-2 py-0.5 rounded font-bold text-[10px] bg-rose-100 text-rose-800">RISKY</span>`;
                } else if (h.risk_classification === "MODERATE") {
                    rBadge = `<span class="px-2 py-0.5 rounded font-bold text-[10px] bg-amber-100 text-amber-800">MODERATE</span>`;
                }

                row.innerHTML = `
                    <td class="py-2.5 px-3 font-medium text-slate-700">${h.inspection_date ? h.inspection_date.slice(0, 16) : 'Recent'}</td>
                    <td class="py-2.5 px-3 font-black text-blue-600">${h.condition_percentage}%</td>
                    <td class="py-2.5 px-3 font-bold text-rose-600">${h.potholes_count}</td>
                    <td class="py-2.5 px-3">${rBadge}</td>
                    <td class="py-2.5 px-3 text-slate-600">${h.inspection_source || 'Inspection'}</td>
                    <td class="py-2.5 px-3 text-slate-500">${h.inspector_name || 'Authority'}</td>
                `;
                tbody.appendChild(row);
            });
        }

        const modal = document.getElementById("road-history-modal");
        if (modal) modal.classList.remove("hidden");
    } catch (e) {
        console.error("Error viewing road history:", e);
        alert("Failed to load road inspection history.");
    }
}

function closeRoadHistoryModal() {
    const modal = document.getElementById("road-history-modal");
    if (modal) modal.classList.add("hidden");
}
