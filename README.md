# RoadGuard AI
## AI-Powered Road Damage Detection, Road Health Monitoring, GIS-Based Road Intelligence & Multi-Route Risk Finder

> *"Detect Road Distress with AI. Monitor Pavement Health over Time. Empower Citizens & Authorities with GIS-Driven Route Risk Intelligence."*

---

## 1. Executive Summary & Platform Overview

Modern civil infrastructure management is challenged by fragmented citizen complaint channels, delayed pavement maintenance, lack of objective damage tracking, and motorist navigation tools that are oblivious to hazardous road distresses.

**RoadGuard AI** is a comprehensive, production-grade AI platform connecting:
1. **AI-Based Road Damage Detection**: Fine-tuned on the multi-country **RDD2022 dataset** with YOLOv8 and ByteTrack multi-object tracking.
2. **Explainable Road Health & Condition Classification**: 3-tier classification (**RISKY / CRITICAL** [Red], **MODERATE** [Yellow], **SAFE** [Green]) with a normalized 0–100% Road Condition Percentage.
3. **Citizen Reporting & Grievance Portal**: Public reporting of road distresses via video or photo with instant AI assessment and a strict **authority verification quarantine**.
4. **Authority Command & Verification Desk**: Dedicated review interface allowing municipal engineers to inspect citizen reports, watch video evidence, and **Accept** (integrating into the official database) or **Reject** (preserving for audit without altering official road records).
5. **Authority Direct Road Inspection**: Independent inspection workflow allowing authorities to survey corridors, run AI tracking, and publish official road updates directly.
6. **Temporal Database Monitoring & Inspection History**: Persistent database tracking condition percentage and pothole counts across inspections over time.
7. **GIS-Based 3-Color Road Condition Map**: Interactive geospatial map of Belagavi City, Karnataka, color-coding road corridors (**RED** for Risky, **YELLOW** for Moderate, **GREEN** for Safe).
8. **Structured Road Condition Table & History Modal**: Complete directory of monitored road corridors with search, risk filtering, and historical timeline inspection.
9. **Damage-Aware Multi-Route Risk Finder**: OSRM driving alternatives over OpenStreetMap road geometry, scored against current verified damage and road-condition records.
10. **Executive Overview Dashboard**: Strictly placed as the **last section** in the platform navigation, rendering a live 3-tier condition distribution chart and 9 real-time summary KPI cards directly from the database.

---

## 2. Platform Architecture

```
                                      +-------------------------------------------------------+
                                      |                     ROADGUARD AI                      |
                                      |              Full-Stack Web Application               |
                                      +-------------------------------------------------------+
                                                                  |
                     +--------------------------------------------+-------------------------------------------+
                     |                                                                                        |
                     v                                                                                        v
       +---------------------------+                                                            +---------------------------+
       |   Dual-Role Frontend UI   |                                                            |      FastAPI Backend      |
       | - Citizen Services Portal |                                                            | - REST API Endpoints      |
       | - Authority Command Desk  | <------------------- HTTP REST / JSON -------------------> | - SQLite / SQLAlchemy ORM |
       | - 3-Color Leaflet GIS Map |                                                            | - Static Media Servicing  |
       | - Multi-Route Risk Finder |                                                            | - AI Inference Pipeline   |
       | - Overview Dashboard      |                                                            |                           |
       +---------------------------+                                                            +---------------------------+
                                                                                                              |
                     +----------------------------------------------------------------------------------------+
                     |
                     +---> [1] AI Vision & Damage Detection Engine (backend/detector.py)
                     |         - YOLOv8m-RDD2022 Primary Multi-Class Detector (D00, D10, D20, D40)
                     |         - High-Recall Pothole Instance Segmentation Model
                     |         - Severity Classification: Minor, Moderate, Severe
                     |
                     +---> [2] Video Multi-Object Tracking Engine (backend/tracker.py)
                     |         - ByteTrack Centroid & IoU Association across video frames
                     |         - Persistent unique ID generation (`POTHOLE-001`, `CRACK-002`)
                     |         - Distinguishes Total Frame Detections from Unique Cataloged Defects
                     |
                     +---> [3] Road Condition & Health Scoring Engine (backend/risk_engine.py)
                     |         - 0-100% Road Condition Percentage (Higher = Better Health)
                     |         - 3-Tier Classification: RISKY (Red), MODERATE (Yellow), SAFE (Green)
                     |
                     +---> [4] Belagavi GIS Network & Multi-Route Risk Finder (backend/gis_belagavi.py)
                     |         - 30 Authentically Mapped Belagavi Corridors & 17 Road Junctions
                     |         - Segment-level condition integration from database
                     |         - Multi-route calculation penalizing high-risk corridors
                     |
                     +---> [5] Citizen Grievance & Authority Verification Lifecycle (backend/app.py)
                     |         - Citizen Submission -> Status: "Pending Verification"
                     |         - Quarantine: Unverified reports never alter official DB, Map, or Routes
                     |         - ACCEPT -> Official RoadSegment updated + RoadInspectionHistory logged
                     |         - REJECT -> Moved to Rejected section, preserved for audit
                     |
                     +---> [6] Central Duplicate Detection & Consolidation Engine (backend/duplicate_engine.py)
                               - Multi-Signal Scoring: GPS Haversine (< 25m) + MobileNetV3 Cosine Embedding + OpenCV dHash + RDD2022 Compatibility
                               - 3-State Classification: CONFIRMED DUPLICATE, NEEDS VERIFICATION, NEW DAMAGE
                               - Video Frame Consolidation via ByteTrack prior to physical record association
                               - Physical Damage Record consolidation with DamageObservation temporal progression
```

---

## 3. Core Functional Modules

| Module | Purpose & Scope | Technology Stack |
|---|---|---|
| **Road Condition Classification** | Computes explainable condition percentage (0-100%) and 3-tier risk classification: **RISKY (Red)**, **MODERATE (Yellow)**, **SAFE (Green)**. | Python, Weighted Multi-Factor Heuristic |
| **Video Damage Analysis** | Dashcam video processing with ByteTrack multi-object tracking to eliminate duplicate pothole counting across frames. | YOLOv8m, ByteTrack, OpenCV |
| **Citizen Reporting Portal** | Public interface to upload road video/photo, pick Belagavi corridor, and submit grievances stored with `Pending Verification`. | HTML5, Tailwind CSS, JavaScript |
| **Authority Verification Desk** | Dedicated workflow to review citizen grievances, inspect video, and **Accept** (update official DB) or **Reject** (archive). | FastAPI, SQLAlchemy ORM |
| **Authority Direct Inspection** | Independent inspection interface allowing municipal authorities to inspect roads and commit official updates directly. | FastAPI, OpenCV, SQLite |
| **Database-Backed History** | Maintains road records and temporal inspection history over time, preventing duplicate road records. | SQLite, SQLAlchemy, Pydantic |
| **GIS Road Condition Map** | Interactive Leaflet map with 30 OSRM-derived Belagavi road corridors, live 3-tier condition colors, and verified-damage pins. | Leaflet.js, OSRM, OpenStreetMap |
| **Road Condition Table** | Structured road register with search, risk filter, condition progress bars, and historical progression modals. | JavaScript DOM, Modal Controller |
| **Multi-Route Risk Finder** | Renders only distinct drivable alternatives returned by OSRM and recommends a route using verified damage exposure and distance. | OSRM, GeoJSON, SQLAlchemy |
| **Duplicate Report Detection** | Multi-signal engine (GPS Haversine, OpenCV dHash, MobileNetV3 deep embeddings, RDD2022 compatibility) consolidating duplicate reports into single physical damage records. | PyTorch MobileNetV3, OpenCV, Haversine |
| **Authority Duplicate Review Desk** | Side-by-side visual photo comparison and audit desk to Confirm Duplicates, Mark Separate Damage, or Reject invalid submissions. | Tailwind CSS, FastAPI, SQLAlchemy ORM |
| **Overview Dashboard** | Strictly placed as the **last section**; renders a Doughnut chart of road distribution and 9 real-time KPI cards from `/api/dashboard/stats`. | Chart.js, FastAPI Aggregations |

---

## 4. Road Condition Classification Formula

Every road monitored by the platform maintains a normalized **Road Condition Percentage** ($C \in [0\%, 100\%]$) and a 3-tier risk classification:

### 4.1 Condition Percentage Formula
$$C = \max\left(0, 100.0 - \left(P_{\text{potholes}} + P_{\text{damage}} + P_{\text{severity}}\right) \times M_{\text{speed}} \times M_{\text{road}}\right)$$

Where:
- **Pothole Penalty ($P_{\text{potholes}}$)**: Each detected pothole deducts $12.5$ points (scaled sublinearly: $\min(55, \text{potholes} \times 12.5)$).
- **Surface Damage Penalty ($P_{\text{damage}}$)**: Non-pothole defects (alligator, longitudinal, transverse cracks) deduct $4.5$ points each.
- **Severity Penalty ($P_{\text{severity}}$)**: Severe distresses deduct an additional $8.0$ points each.
- **Speed Limit Multiplier ($M_{\text{speed}}$)**:
  - $\ge 80\text{ km/h}$ (Expressway/Highway): $1.25$
  - $\ge 60\text{ km/h}$ (Arterial): $1.10$
  - $\ge 50\text{ km/h}$ (City Road): $1.00$
  - $< 50\text{ km/h}$ (Local/Residential): $0.85$
- **Road Class Multiplier ($M_{\text{road}}$)**:
  - Highway: $1.20$
  - Arterial: $1.10$
  - Local: $1.00$
  - Residential: $0.90$

### 4.2 Three-Tier Classification Thresholds
- **RISKY / CRITICAL (RED)**:
  - Road Condition Percentage $< 50\%$, **OR**
  - Detected severe potholes $\ge 2$, **OR**
  - Critical damage detected on high-speed roads ($\ge 60\text{ km/h}$).
  - *Action*: Emergency repair order dispatched within 24 hours.
- **MODERATE (YELLOW)**:
  - Road Condition Percentage between $50\%$ and $79\%$.
  - Noticeable surface wear requiring scheduled maintenance within 7–14 days.
- **SAFE (GREEN)**:
  - Road Condition Percentage $\ge 80\%$.
  - Sound pavement with minimal or no structural distress.

---

## 5. Citizen Grievance & Authority Verification Lifecycle

To prevent false alarms or unverified complaints from distorting official infrastructure records, RoadGuard AI implements a strict verification quarantine:

```
[Citizen Submission]
        |
        v
[AI Damage Analysis] (Instant Pothole Detection & Condition Evaluation)
        |
        v
[Stored in Database] (Status: "Pending Verification")
        |
        +---> [OFFICIAL DATABASE QUARANTINE]
        |     - Official RoadSegment record NOT changed
        |     - GIS Road Map NOT changed
        |     - Multi-Route Risk Finder NOT changed
        |
        v
[Authority Verification Desk] (Civil Engineer Reviews Video & AI Analysis)
        |
        +-----------------------------------+-----------------------------------+
        |                                                                       |
        v [ACCEPT ACTION]                                                       v [REJECT ACTION]
1. Update Submission status to ACCEPTED.                                1. Update Submission status to REJECTED.
2. Update RoadSegment condition %, potholes, and risk.                  2. Move to separate Rejected Reports section.
3. Append historical record to RoadInspectionHistory.                  3. Preserve report and evidence for audit.
4. Refresh GIS Map with updated 3-color polylines.                     4. Do NOT alter official road database.
5. Include updated road condition in Multi-Route Finder.                5. Do NOT alter GIS Map or Route Finder.
6. Refresh Road Condition Table & Dashboard Stats.
```

---

## 6. Belagavi Demonstration Dataset

The platform is initialized with authentic baseline road data covering **30 major corridors** in **Belagavi (Belgaum), Karnataka**:

```
==================================================================================================
Total Monitored Corridors : 30
Risky / Critical (Red)    : 6 Corridors (NH-48 Expressway, Khanapur Rd, SPM Flyover, Maratha Link...)
Moderate (Yellow)         : 10 Corridors (College Rd, Hindwadi Cross, Vadgaon Connector, Old PB Rd...)
Safe (Green)              : 14 Corridors (Congress Rd, Camp Boulevard, Civil Hospital Rd, Kakaves...)
Total Detected Potholes   : 46 Active Cavities
City-Wide Avg Condition   : 75.2%
==================================================================================================
```

### Belagavi Road Network Corridors Included:
1. `BLG-SEG-01`: Khanapur Road (Tilakwadi to 3rd Gate) - **RISKY (38.5%)**
2. `BLG-SEG-02`: Khanapur Road (3rd Gate to Udyambag) - **SAFE (88.0%)**
3. `BLG-SEG-03`: Congress Road (Chennamma Circle to 1st Gate) - **SAFE (94.0%)**
4. `BLG-SEG-04`: College Road (Bogarves to Hindwadi) - **MODERATE (76.5%)**
5. `BLG-SEG-05`: Hindwadi to RPD College Cross - **SAFE (91.0%)**
6. `BLG-SEG-06`: Civil Hospital Road (Chennamma to Fort Lake) - **SAFE (92.5%)**
7. `BLG-SEG-07`: Camp Boulevard (Chennamma to Camp Church) - **SAFE (95.0%)**
8. `BLG-SEG-08`: Camp Church to Bogarves Corridor - **SAFE (90.0%)**
9. `BLG-SEG-09`: NH-48 Belagavi Expressway (Kanbargi to Ramteerth) - **RISKY (32.0%)**
10. `BLG-SEG-10`: NH-48 Belagavi Expressway (Ramteerth to Gandhi Nagar) - **RISKY (45.0%)**
11. `BLG-SEG-11`: NH-48 Bypass (Gandhi Nagar to Halaga Interchange) - **SAFE (86.0%)**
12. `BLG-SEG-12`: Fort Road to Gandhi Nagar Link - **SAFE (89.5%)**
13. `BLG-SEG-13`: Sambhaji Chowk to Shahapur Market - **MODERATE (74.0%)**
14. `BLG-SEG-14`: Shahapur to Vadgaon Main Road - **MODERATE (66.5%)**
15. `BLG-SEG-15`: Vadgaon to Udyambag Industrial Connector - **MODERATE (62.0%)**
16. `BLG-SEG-16`: Old PB Road (Sambhaji Chowk to Chennamma) - **MODERATE (71.5%)**
17. `BLG-SEG-17`: Khade Bazar Arterial (Bogarves to Sambhaji) - **SAFE (93.0%)**
18. `BLG-SEG-18`: Congress Road Extension (1st Gate to 3rd Gate) - **SAFE (96.5%)**
19. `BLG-SEG-19`: Khanapur Cross (3rd Gate to RPD College) - **SAFE (98.0%)**
20. `BLG-SEG-20`: RPD Corner to Udyambag Link - **SAFE (95.0%)**
21. `BLG-SEG-21`: SPM Road Overbridge (Sambhaji to 1st Gate) - **RISKY (46.0%)**
22. `BLG-SEG-22`: Kanbargi Road (Fort Lake to Kanbargi Cross) - **SAFE (94.5%)**
23. `BLG-SEG-23`: Halaga-Vadgaon Ring Corridor - **MODERATE (72.0%)**
24. `BLG-SEG-24`: Camp Cantonment to Hindwadi Military Cross - **SAFE (97.0%)**
25. `BLG-SEG-25`: Kakaves Road (Chennamma to Civil Hospital) - **SAFE (93.5%)**
26. `BLG-SEG-26`: Civil Hospital to Fort Lake Corridor - **SAFE (92.0%)**
27. `BLG-SEG-27`: Nath Pai Circle Road (Shahapur to 1st Gate) - **MODERATE (68.0%)**
28. `BLG-SEG-28`: Maratha Colony Link (Vadgaon to 3rd Gate) - **RISKY (44.5%)**
29. `BLG-SEG-29`: Hindwadi to 1st Gate Cross - **MODERATE (78.0%)**
30. `BLG-SEG-30`: Tilakwadi 1st Gate to Bogarves West Arterial - **MODERATE (75.0%)**

---

## 7. Central Duplicate Report Detection & Multi-Signal Matching Architecture

### 7.1 Objective & Design Principles
In municipal road management, citizens and road survey vehicles frequently submit different photos, videos, and grievances of the exact same physical pothole from different angles, times of day, lighting conditions, or smartphone GPS accuracies. Creating distinct database records for each submission inflates repair backlogs, skews city road health statistics, and distorts GIS route risk calculations.

**RoadGuard AI** implements a centralized multi-signal **Duplicate Report Detection Engine** (`backend/duplicate_engine.py`) that:
1. **Consolidates** multiple submissions referring to the same physical pothole into a single ground-truth `PhysicalDamageRecord`.
2. **Preserves** every independent citizen report, photo, video, and survey in `Submission`, `AIDetection`, and `DamageObservation` for complete transparency and historical progression.
3. **Decouples** temporary video tracking IDs (`POTHOLE-001`) from permanent physical database IDs.

---

### 7.2 Multi-Signal Matching Pipeline
Every incoming citizen grievance and authority inspection is evaluated through four complementary matching signals:

```
                            +-------------------------------------------+
                            |           INCOMING ROAD DEFECT            |
                            | (GPS: Lat/Lon, Image/Crop, Category Code) |
                            +-------------------------------------------+
                                                  |
              +-------------------+---------------+-------------------+-------------------+
              |                   |                                   |                   |
              v                   v                                   v                   v
     [1] GPS Proximity   [2] Deep Embedding                  [3] Perceptual Hash   [4] Category Compatibility
     - Haversine Dist    - PyTorch MobileNetV3-Small         - OpenCV 64-bit dHash - RDD2022 Match Matrix
     - Belagavi Boundary - 576-dim L2 Normalized Vector      - Bitwise Hamming     - D00, D10, D20, D40
     - Radius: R <= 25m  - Cosine Similarity (Angle/Light)   - Hamming Similarity  - Penalize Incompatible
              |                   |                                   |                   |
              +-------------------+---------------+-------------------+-------------------+
                                                  |
                                                  v
                               +-------------------------------------+
                               |   WEIGHTED MULTI-SIGNAL SCORER      |
                               |   W = 0.35*Geo + 0.35*Emb +         |
                               |       0.15*dHash + 0.15*Cat         |
                               +-------------------------------------+
                                                  |
                                                  v
                      +---------------------------+---------------------------+
                      |                                                       |
                      v                                                       v
         W >= 0.75 (or tight visual)                             0.45 <= W < 0.75
           [CONFIRMED DUPLICATE]                               [NEEDS VERIFICATION]
         - Link to PhysicalDamageRecord                       - Flag for Manual Review
         - times_observed += 1                                - Side-by-Side Photo Compare
         - Add DamageObservation                              - Authority Review Desk
```

#### Signal 1: Geographic Proximity ($S_{\text{geo}}$)
- Computes great-circle distance using the **Haversine formula** between candidate coordinates and existing physical damage records within the Belagavi boundary:
  $$d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
- Normalized spatial score within configurable search radius ($R = 25\text{m}$):
  $$S_{\text{geo}} = \max\left(0, 1.0 - \frac{d}{R}\right)$$
- If $d > R$, candidate records outside the search radius are excluded.

#### Signal 2: Deep Neural Embedding Cosine Similarity ($S_{\text{emb}}$)
- To achieve robustness across camera angles, perspective shifts, and variable sunlight/shadowing where simple pixel-level hashes drop:
- Employs a pretrained `MobileNetV3-small` convolutional backbone (PyTorch torchvision) as a headless feature extractor:
  $$\mathbf{v} = \frac{f_{\text{mobilenet}}(I)}{\|f_{\text{mobilenet}}(I)\|_2} \in \mathbb{R}^{576}$$
- Evaluates visual similarity using cosine distance:
  $$S_{\text{emb}} = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2}$$
- Fallback: Multi-channel spatial color histogram matching via OpenCV if neural weights are unavailable.

#### Signal 3: Perceptual Difference Hashing ($S_{\text{dHash}}$)
- Resizes defect crops to $9 \times 8$ grayscale, evaluates horizontal gradient brightness differences, and builds a compact 64-bit binary fingerprint.
- Evaluates bitwise Hamming distance $H$:
  $$S_{\text{dHash}} = 1.0 - \frac{H}{64}$$

#### Signal 4: Damage Category Compatibility ($S_{\text{cat}}$)
- Verifies compatibility across RDD2022 distress classifications:
  - Exact category match (e.g. `D40` Pothole == `D40` Pothole): $1.0$
  - Structurally related distress (e.g. `D20` Alligator Crack & `D40` Pothole): $0.5$
  - Incompatible distress (e.g. `D00` Longitudinal Crack vs `D40` Pothole): $0.0$

#### Composite Score Formulation:
$$W = w_{\text{geo}} S_{\text{geo}} + w_{\text{emb}} S_{\text{emb}} + w_{\text{dhash}} S_{\text{dHash}} + w_{\text{cat}} S_{\text{cat}}$$
*(Default calibration: $w_{\text{geo}} = 0.35$, $w_{\text{emb}} = 0.35$, $w_{\text{dhash}} = 0.15$, $w_{\text{cat}} = 0.15$)*

---

### 7.3 3-State Classification & Decision Logic

1. **`CONFIRMED DUPLICATE`** ($W \ge 0.75$, or $d \le 12\text{m}$ with $S_{\text{emb}} \ge 0.72$):
   - Strong multi-signal evidence that the report refers to an existing known physical pothole.
   - Pre-links `submission.physical_damage_id` to the existing `PhysicalDamageRecord`.
   - On authority verification:
     - Does **not** create a new row in `physical_damage_records`.
     - Increments `times_observed` by 1.
     - Updates `latest_inspection_date = now()`.
     - Appends an audit entry to `DamageObservation` with observed severity and area changes.
     - Sets `duplicate_matches.status = 'Merged'`.

2. **`NEEDS VERIFICATION`** ($0.45 \le W < 0.75$):
   - Spatial proximity or partial visual resemblance is present, but evidence is ambiguous (e.g. two potholes 8 meters apart on the same street, or different crack types).
   - Flagged with status `Needs_Verification` and routed to the **Authority Duplicate Review Desk** (`#tab-duplicates`).
   - Does **not** automatically merge records without civil engineer sign-off.

3. **`NEW DAMAGE`** ($W < 0.45$):
   - No matching physical record exists within the spatial radius.
   - Marked as `Unique`. Upon verification, provisions a brand-new `PhysicalDamageRecord` (`BLG-DMG-XXXX`).

---

### 7.4 Video Frame-Level Deduplication vs Submission Deduplication

The platform cleanly separates the two levels of duplicate prevention:
1. **Frame-Level Tracking**: In dashcam video feeds, the same pothole appears across 15–60 consecutive video frames. The **ByteTrack tracker** (`backend/tracker.py`) uses centroid tracking and IoU overlap to maintain a single continuous track (`POTHOLE-001`). Frame-level detections are consolidated into **one observation per tracked defect**.
2. **Submission-Level Deduplication**: After video frames are consolidated into unique tracked defects, each tracked defect passes through the central duplicate engine to check if it matches a pre-existing physical damage record from previous citizen reports or past surveys.

---

### 7.5 Authority Duplicate Review Desk
Located in the Authority Portal under **Duplicate Management & Verification** (`#tab-duplicates`):
- **Side-by-Side Visual Comparison**: Displays candidate photo alongside existing official damage evidence photo.
- **Multi-Signal Telemetry Chips**: Live display of GPS Distance (m), Perceptual Hash match %, Deep Neural Cosine Similarity %, and Overall Score %.
- **3 Authority Actions**:
  1. `Confirm Duplicate`: Merges candidate submission into the existing physical record, updates inspection count, and logs observation history.
  2. `Mark as Separate Damage`: Confirms the defect is distinct; provisions a new independent `PhysicalDamageRecord`.
  3. `Reject Report`: Discards candidate report as invalid without affecting official records.

---

### 7.6 Downstream Impact on GIS Map & Multi-Route Risk Finder
- **GIS Map Pins**: The public Leaflet GIS map queries `/api/physical-damage`, which exclusively renders consolidated `PhysicalDamageRecord`s with `verification_status == 'Verified'`. Duplicate citizen reports do not generate redundant pins.
- **Road Geometry**: The shared road catalog contains 30 full road geometries routed by OSRM over OpenStreetMap data. The database stores those geometries and their source/update metadata; the public and authority maps read the same `/api/roads/condition` data.
- **Route Risk Scoring**: Each OSRM alternative is checked against verified, unrepaired physical-damage GPS records within 35 m and matching database road corridors. Repaired, closed, unverified, and rejected records do not contribute to active exposure.
- **Route Selection**: The recommendation score is `distance_km + 0.05 × exposure_score`. It is an explicit distance-versus-risk tradeoff, not a shortest-path graph approximation.

### 7.7 OpenStreetMap Geometry & OSRM Routing
- The public road-condition map uses a bundled snapshot of 30 real OSRM route geometries so it can load without making 30 live requests. Refresh it with `python scripts/sync_osm_roads.py`; a successful refresh is required before the updated catalog is applied to the database at the next application startup.
- Set `ROADVISION_OSRM_URL` to a self-hosted OSRM-compatible endpoint when available. The default is `https://router.project-osrm.org`; `ROADVISION_OSRM_TIMEOUT` controls the request timeout in seconds (default `12`).
- Navigation requests use the configured OSRM service at request time. If it is unavailable or has no route, the API reports the failure and does not fall back to generated routes. The number of alternatives is whatever distinct routes OSRM returns (the public demo often returns fewer than three).
- Keep OpenStreetMap attribution visible on maps and when displaying route geometry. The default public OSRM demo is subject to its availability and usage policy; use a suitable hosted or self-managed service for production workloads.

---

## 8. AI Model Architecture & Benchmark

In strict adherence to project directives, generic COCO models were replaced with models trained specifically on the **RDD2022 multi-country road damage dataset**:

| Category Code | Damage Classification | Structural Hazard Profile |
|---|---|---|
| **D00** | Longitudinal Crack | Pavement surface fracture running parallel to traffic direction |
| **D10** | Transverse Crack | Cross-lane fracture resulting from thermal contraction |
| **D20** | Alligator / Fatigue Crack | Interconnected structural mesh cracks indicating sub-base failure |
| **D40** | Pothole | Bowl-shaped cavity resulting from moisture ingress and wheel impact |

### Empirical Test Benchmark Results
Evaluated on held-out test splits with ground-truth COCO annotations:

```
==================================================================================================
Model Checkpoint                Architecture      Precision   Recall   F1-Score   mAP@50   FPS
==================================================================================================
roadvision_rdd2022_yolov8m.pt   YOLOv8 Medium     100.00%     20.00%   0.3333     0.5700   1.0
keremberke_yolov8n_pothole.pt   YOLOv8 Nano Seg    66.67%     80.00%   0.7273     0.6967   8.7
dronefreak_rdd2022_yolov8s.pt   YOLOv8 Small        0.00%      0.00%   0.0000     0.0000   4.2
==================================================================================================
```

---

## 9. Database Architecture

SQLite database located at `data/roadvision.db` modeled with SQLAlchemy:

- **`road_segments`**: Monitored corridors, road code (`BLG-SEG-01`), road name, location, road class, speed limit, coordinates polyline, potholes count, condition percentage, risk classification, last inspected date, inspection source, verification status.
- **`road_inspection_history`**: Historical timeline tracking condition progression over time (`road_segment_id`, `inspection_date`, `potholes_count`, `condition_percentage`, `risk_classification`, `inspection_source`, `inspector_name`, `notes`).
- **`submissions`**: Citizen and authority survey reports with upload media paths, AI detection stats, status (`Pending Verification`, `ACCEPTED`, `REJECTED`), `physical_damage_id`, `duplicate_status` (`Unique`, `Confirmed_Duplicate`, `Needs_Verification`, `Resolved_Duplicate`), verified by, and verification notes.
- **`physical_damage_records`**: Consolidated ground-truth defects mapped to specific road segments with audited coordinates, `times_observed`, `first_reported_date`, `latest_inspection_date`, `image_hash`, `image_embedding` (MobileNetV3 576-dim feature vector), and relationship to historical observations.
- **`damage_observations`**: Temporal progression history of each physical damage record (`physical_damage_id`, `submission_id`, `observation_date`, `observed_severity`, `observed_area_pct`, `condition_state`, `evidence_photo_path`, `observer_type`, `notes`).
- **`duplicate_matches`**: Spatial Haversine distance, visual dHash similarity, MobileNetV3 embedding cosine similarity, overall matching score, decision status, decision reason, side-by-side evidence photos, and resolution audit.
- **`repair_records`**: Municipal Kanban work-orders (`Detected` &rarr; `Assigned` &rarr; `In Progress` &rarr; `Repaired` &rarr; `Closed`).

---

## 10. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web application single-page interface |
| `GET` | `/api/dashboard/stats` | Live overview statistics (9 KPI metrics + road condition distribution) |
| `GET` | `/api/roads/condition` | List of monitored roads with condition %, potholes, and risk classification |
| `GET` | `/api/roads/{id}/history` | Historical timeline of condition progression for a specific road |
| `POST` | `/api/citizen/report` | Citizen grievance reporting endpoint with AI damage evaluation & duplicate pre-check |
| `GET` | `/api/citizen/my-reports` | Track submitted citizen grievances and their verification statuses |
| `GET` | `/api/authority/citizen-reports` | List citizen submissions filterable by `pending`, `accepted`, `rejected`, or `all` |
| `POST` | `/api/authority/reports/{id}/verify` | Authority verification action: **ACCEPT** or **REJECT** report (merges duplicates) |
| `POST` | `/api/roads/inspect` | Authority direct road inspection and official database update (checks duplicate engine) |
| `POST` | `/api/inspect/video` | Upload video for ByteTrack multi-object tracking and report generation |
| `POST` | `/api/inspect/image` | Upload image for multi-class RDD2022 defect detection |
| `POST` | `/api/routes/navigate` | Compute multi-path routes incorporating live database road conditions |
| `GET` | `/api/physical-damage` | Retrieve verified physical damage pins for GIS map rendering |
| `GET` | `/api/physical-damage/{id}/history` | Retrieve complete observation history timeline of a physical damage record |
| `GET` | `/api/duplicates` | Retrieve duplicate candidates for authority review with side-by-side photo comparison |
| `POST` | `/api/duplicates/{id}/resolve` | Resolve duplicate: **CONFIRM_DUPLICATE**, **MARK_SEPARATE**, or **REJECT_REPORT** |
| `GET` | `/api/models/benchmark` | Retrieve empirical held-out test benchmark metrics |
| `GET` | `/api/reports/{id}/export/{fmt}` | Download inspection report in `pdf`, `csv`, or `json` format |

---

## 11. Project Directory Layout

```
ROADVISION AI/
├── backend/
│   ├── app.py                  # FastAPI application with citizen & authority endpoints
│   ├── config.py               # Global settings, paths, thresholds, and weights
│   ├── database.py             # SQLite engine, schema migration, and Belagavi seeding
│   ├── models_db.py            # SQLAlchemy schemas (RoadSegment, History, Submission...)
│   ├── detector.py             # YOLOv8 RDD2022 road defect computer vision detector
│   ├── tracker.py              # Persistent ByteTrack video multi-object tracking
│   ├── gis_belagavi.py         # Belagavi 30 corridors, boundary checks & risk routing
│   ├── risk_engine.py          # 3-tier road classification & condition percentage formula
│   ├── duplicate_engine.py     # Multi-signal duplicate detection & consolidation engine
│   ├── progress_monitor.py     # Historical temporal comparison & composite evidence
│   └── report_generator.py     # PDF/HTML, CSV, and JSON report serializers
├── frontend/
│   ├── static/
│   │   ├── css/style.css       # Clean white theme styling and glassmorphism
│   │   └── js/
│   │       ├── app.js          # Unified controller, role switching, verification & duplicate review
│   │       └── map.js          # Leaflet GIS map with 3-tier colors and route rendering
│   └── templates/
│       └── index.html          # Single-page interface (Overview Dashboard as LAST section)
├── models/
│   ├── primary/
│   │   └── roadvision_rdd2022_yolov8m.pt  # Primary 4-class RDD2022 model (49.6 MB)
│   ├── alternative/
│   │   ├── dronefreak_rdd2022_yolov8s.pt  # Lightweight multi-class model (21.5 MB)
│   │   └── keremberke_yolov8n_pothole.pt  # Pothole segmentation model (6.4 MB)
│   └── benchmark/                         # Held-out benchmark metrics and summaries
├── data/
│   ├── uploads/                # Uploaded inspection media
│   ├── outputs/                # Annotated images and tracked videos
│   ├── reports/                # Exported reports
│   └── roadvision.db           # Persistent SQLite database
├── tests/
│   ├── test_duplicate_detection_scenarios.py  # 10 mandatory duplicate detection scenarios
│   ├── test_roadguard_integration.py          # 7 integration tests covering citizen & authority flows
│   ├── test_belagavi_integration.py           # Belagavi network and routing tests
│   ├── test_api.py                            # REST API endpoints and CRUD tests
│   ├── test_detector.py                       # Detection and severity tests
│   ├── test_tracker.py                        # ByteTrack ID persistence tests
│   ├── test_duplicate.py                      # Multi-signal duplicate unit tests
│   ├── test_risk.py                           # Risk formula tests
│   └── test_progress.py                       # Temporal progress monitoring tests
├── run_server.py               # Application launcher
├── run.bat                     # Windows startup script
├── requirements.txt            # Python dependencies
└── README.md                   # Platform documentation
```

---

## 12. Installation & Local Startup

### Prerequisites:
- Python 3.10+ (Tested on Python 3.13.2)
- Windows, macOS, or Linux
- Web Browser (Chrome, Edge, Firefox)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Launch Application Server
```bash
python run_server.py
```

### Step 3: Access Platform
- **RoadGuard AI Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger REST API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 13. Automated Test Suite Execution

Run the complete 50-test automated verification suite:
```bash
pytest -v
```

### Verified Test Summary (50 Passed):
```
tests/test_api.py::test_health_check_endpoint PASSED                     [  2%]
tests/test_api.py::test_get_inspections_endpoint PASSED                  [  4%]
tests/test_api.py::test_get_defects_endpoint PASSED                      [  6%]
tests/test_api.py::test_analytics_endpoint PASSED                        [  8%]
tests/test_api.py::test_duplicates_endpoint PASSED                       [ 10%]
tests/test_api.py::test_repairs_endpoint PASSED                          [ 12%]
tests/test_api.py::test_models_benchmark_endpoint PASSED                 [ 14%]
tests/test_belagavi_integration.py::test_belagavi_boundary_validation PASSED [ 16%]
tests/test_belagavi_integration.py::test_api_gis_belagavi_info PASSED    [ 18%]
tests/test_belagavi_integration.py::test_api_road_segments PASSED        [ 20%]
tests/test_belagavi_integration.py::test_spatial_segment_matching PASSED [ 22%]
tests/test_belagavi_integration.py::test_route_navigation_within_belagavi PASSED [ 24%]
tests/test_belagavi_integration.py::test_route_navigation_blocks_outside_belagavi PASSED [ 26%]
tests/test_belagavi_integration.py::test_three_state_defect_lifecycle PASSED [ 28%]
tests/test_belagavi_integration.py::test_physical_damage_api_only_returns_verified PASSED [ 30%]
tests/test_detector.py::test_detector_initialization PASSED              [ 32%]
tests/test_detector.py::test_severity_classification PASSED              [ 34%]
tests/test_detector.py::test_perceptual_dhash PASSED                     [ 36%]
tests/test_detector.py::test_image_inference_real_file PASSED            [ 38%]
tests/test_detector.py::test_missing_image_handling PASSED               [ 40%]
tests/test_duplicate.py::test_haversine_distance PASSED                  [ 42%]
tests/test_duplicate.py::test_hamming_similarity PASSED                  [ 44%]
tests/test_duplicate.py::test_duplicate_candidate_evaluation_same_location PASSED [ 46%]
tests/test_duplicate.py::test_duplicate_candidate_different_locations PASSED [ 48%]
tests/test_duplicate_detection_scenarios.py::test_scenario_1_same_pothole_different_citizens PASSED [ 50%]
tests/test_duplicate_detection_scenarios.py::test_scenario_2_same_pothole_different_angles_lighting PASSED [ 52%]
tests/test_duplicate_detection_scenarios.py::test_scenario_3_distinct_nearby_potholes PASSED [ 54%]
tests/test_duplicate_detection_scenarios.py::test_scenario_4_video_frame_consolidation PASSED [ 56%]
tests/test_duplicate_detection_scenarios.py::test_scenario_5_citizen_report_followed_by_authority_inspection PASSED [ 58%]
tests/test_duplicate_detection_scenarios.py::test_scenario_6_ambiguous_match_flagged_for_verification PASSED [ 60%]
tests/test_duplicate_detection_scenarios.py::test_scenario_7_brand_new_pothole_creation PASSED [ 62%]
tests/test_duplicate_detection_scenarios.py::test_scenario_8_historical_progression_over_time PASSED [ 64%]
tests/test_duplicate_detection_scenarios.py::test_scenario_9_data_integrity_cascade_orphan_prevention PASSED [ 66%]
tests/test_duplicate_detection_scenarios.py::test_scenario_10_downstream_impact_on_gis_map_and_route_navigation PASSED [ 68%]
tests/test_progress.py::test_progress_monitoring_repaired PASSED         [ 70%]
tests/test_progress.py::test_progress_monitoring_worsened PASSED         [ 72%]
tests/test_progress.py::test_progress_monitoring_stable PASSED           [ 74%]
tests/test_risk.py::test_empty_defects_zero_risk PASSED                  [ 76%]
tests/test_risk.py::test_critical_risk_highway_severe_potholes PASSED    [ 78%]
tests/test_risk.py::test_minor_crack_residential_low_risk PASSED         [ 80%]
tests/test_risk.py::test_score_bounded_0_to_100 PASSED                   [ 82%]
tests/test_roadguard_integration.py::test_road_conditions_api PASSED     [ 84%]
tests/test_roadguard_integration.py::test_road_conditions_filtering PASSED [ 86%]
tests/test_roadguard_integration.py::test_road_history_api PASSED        [ 88%]
tests/test_roadguard_integration.py::test_dashboard_stats_api PASSED     [ 90%]
tests/test_roadguard_integration.py::test_citizen_report_submission_and_lifecycle PASSED [ 92%]
tests/test_roadguard_integration.py::test_citizen_report_rejection_lifecycle PASSED [ 94%]
tests/test_roadguard_integration.py::test_authority_direct_inspection_api PASSED [ 96%]
tests/test_tracker.py::test_box_iou_calculation PASSED                   [ 98%]
tests/test_tracker.py::test_persistent_unique_tracking PASSED            [100%]
====================== 50 passed in 33.67s =======================
```

---

## 14. Hackathon Demonstration Guide

### Scenario 1: Citizen Road Distress Report & Instant AI Feedback
1. Click **"Switch Portal / Sign In"** in the top navigation bar and select **Citizen / Public End** (*Priya Sharma*).
2. Go to **Report Road Damage**.
3. Select or type a Belagavi road name (e.g., `Khanapur Road (Tilakwadi to 3rd Gate)`).
4. Set Road Class to **Arterial**, Speed Limit to **60 km/h**, and select a road photo or video.
5. Click **Submit Grievance to Authority**.
6. Observe the instant ticket generation (`#CIT-BLG-...`), detected potholes count, condition %, damage severity, and the **"Awaiting Authority Verification"** banner.
7. Switch to **Track My Grievances** to verify the ticket is marked with the amber badge: `⏳ Pending Verification`.

### Scenario 2: Verification Quarantine Check
1. Go to **Public Road Condition Map** and the **Multi-Route Risk Finder**.
2. Notice that the unverified citizen report has **not** altered the official road condition database or route calculation.

### Scenario 3: Authority Review & Report Acceptance
1. Click **"Switch Portal / Sign In"** and select **Authority / PWD End** (*Er. Rajesh Verma*).
2. The portal immediately opens to the **Citizen Reports Verification Desk**.
3. Under **Pending Verification**, click to inspect the submitted citizen report.
4. Review the video/photo evidence, detected potholes, road condition %, and risk tier.
5. Click **"Accept Report & Update Official Database"**.
6. Confirm the action. Observe that:
   - The report status transitions to `✓ Accepted & Verified`.
   - The official road condition in the database is updated.
   - A new record is added to `RoadInspectionHistory`.
   - The **GIS Road Condition Map**, **Road Condition Table**, **Multi-Route Risk Finder**, and **Overview Dashboard** are immediately refreshed.

### Scenario 4: Authority Review & Report Rejection
1. In the **Citizen Reports Verification Desk**, review an invalid citizen report.
2. Click **"Reject Report"**.
3. Notice that the report moves to the **Rejected Reports** tab, preserving the audit trail without modifying the official road condition database or map.

### Scenario 5: Duplicate Report Detection & Authority Resolution Desk
1. A citizen submits a report for a pothole near `Tilakwadi` on `Khanapur Road`.
2. Another citizen submits a photo of the same pothole taken 5 meters away with different phone angle and lighting.
3. The multi-signal duplicate engine extracts `MobileNetV3` deep embeddings and evaluates GPS proximity.
4. The system flags the report as **Confirmed Duplicate** or **Needs Verification** without creating redundant physical records.
5. In the Authority Portal, navigate to **Duplicate Verification Desk** (`#tab-duplicates`).
6. Inspect the side-by-side evidence photo comparison cards, GPS distance, deep neural embedding similarity %, perceptual hash %, and overall score.
7. Click **"Confirm Duplicate"** to merge into the ground-truth physical damage record (`times_observed` increments, `DamageObservation` logged) or **"Mark as Separate Damage"** if distinct.

### Scenario 6: Authority Independent Road Inspection & Direct Update
1. In the Authority Portal, navigate to **Video Road Inspection & Direct Update**.
2. Select a road corridor, set Road Class to **Highway**, Speed Limit to **80 km/h**, and select an inspection video.
3. Click **Process & Track Video**.
4. Observe the ByteTrack multi-object tracking HUD, unique pothole count, road condition %, and the green confirmation banner:
   *`Official Inspection Saved: Verified road condition recorded in database.`*

### Scenario 7: 3-Color GIS Road Map & Road Condition Table
1. Navigate to **GIS Road Condition Map**:
   - Inspect the 30 Belagavi corridors rendered in **RED** (Risky), **YELLOW** (Moderate), and **GREEN** (Safe).
   - Click any road polyline to open the popup showing road name, location, potholes count, condition %, risk level, last inspected date, and road class.
   - Use the filter buttons to isolate *Risky (Red)*, *Moderate (Yellow)*, or *Safe (Green)* roads.
2. Navigate to **Road Condition Table & History**:
   - Search by road name (e.g. `Khanapur`).
   - Click **"View History"** on any road to open the **Road Inspection History Modal** and view the temporal evolution of condition percentage, potholes, and audit source across surveys.

### Scenario 8: Damage-Aware Multi-Route Risk Finder
1. Navigate to **Multi-Route Risk Finder**.
2. Select an origin and destination from the OSM road-location selectors, or click two points on the map.
3. Click **Calculate OSRM Routes & Risk**.
4. Inspect the actual OSRM GeoJSON routes, returned distances and durations, verified-damage markers, risk colors, and the distance/risk recommendation score. The result count may be below three when OSRM has no distinct alternatives.

### Scenario 9: Executive Overview Dashboard (The Last Section)
1. Navigate to **Overview Dashboard** (the final item in the sidebar navigation).
2. Review the live 3-tier distribution Doughnut chart (**Risky Red**, **Moderate Yellow**, **Safe Green**).
3. Review the 9 real-time KPI cards:
   - Total Monitored Roads (`30`)
   - Risky Roads (`6`)
   - Moderate Roads (`10`)
   - Safe Roads (`14`)
   - Total Potholes (`46`)
   - Average Road Condition (`75.2%`)
   - Pending Citizen Reports
   - Accepted Reports
   - Rejected Reports

---

## 15. License & Attribution

- **RoadGuard AI Platform**: MIT License.
- **YOLOv8m-RDD2022 Checkpoint**: Creative Commons Attribution 4.0 International (CC BY 4.0).
- **YOLOv8n-Pothole-Seg Checkpoint**: MIT License.
- Developed autonomously for the **Hack Valley National AI/ML Hackathon**.
