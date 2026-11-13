# ROADVISION AI — AI-Based Road Damage and Pothole Detection System
**Problem Statement PS 02 | Domain: Artificial Intelligence & Machine Learning**

---

## Executive Summary & System Status

The **ROADVISION AI** platform is an automated road-monitoring and infrastructure intelligence system built using computer vision, multi-object video tracking, explainable risk assessment, geospatial mapping, and automated reporting.

- **Web Dashboard**: http://127.0.0.1:8000/
- **Interactive REST API Documentation**: http://127.0.0.1:8000/docs
- **Health Check Endpoint**: http://127.0.0.1:8000/api/health
- **Automated Test Suite**: 25/25 unit & integration tests passing (`pytest`)

---

## 1. System Architecture & Tech Stack

```
                                  +-------------------------------------------------------+
                                  |                     ROADVISION AI                     |
                                  |              Full-Stack Web Application               |
                                  +-------------------------------------------------------+
                                                              |
                  +-------------------------------------------+-------------------------------------------+
                  |                                                                                       |
                  v                                                                                       v
    +---------------------------+                                                           +---------------------------+
    |        Frontend UI        |                                                           |      FastAPI Backend      |
    | - Tailwind CSS & Lucide   |                                                           | - REST API Endpoints      |
    | - Leaflet.js GIS Mapping  | <------------------ HTTP REST / JSON -------------------> | - SQLite / SQLAlchemy ORM |
    | - Chart.js Analytics      |                                                           | - Static Media Servicing  |
    +---------------------------+                                                           +---------------------------+
                                                                                                          |
                  +---------------------------------------------------------------------------------------+
                  |
                  +---> [1] AI Vision Engine (models/primary/roadvision_rdd2022_yolov8m.pt)
                  |         - Multi-Class RDD2022 Detection (D00, D10, D20, D40)
                  |         - High-Recall Pothole Instance Segmentation (models/alternative/keremberke_yolov8s_pothole_seg.pt)
                  |         - Bounding Box & Severity Classification (Minor, Moderate, Severe)
                  |
                  +---> [2] Video Multi-Object Tracking Engine (backend/tracker.py)
                  |         - ByteTrack Centroid & IoU Association across consecutive frames
                  |         - Persistent unique ID generation (POTHOLE-001, CRACK-002)
                  |         - Annotated MP4 video output rendering with heads-up telemetry HUD
                  |
                  +---> [3] Duplicate Detection Engine (backend/duplicate_engine.py)
                  |         - Great-Circle Haversine distance (< 25m radius)
                  |         - 64-bit perceptual dHash visual similarity matching (>= 75%)
                  |
                  +---> [4] Explainable Infrastructure Risk Engine (backend/risk_engine.py)
                  |         - Normalized 0-100 composite risk scoring
                  |         - Environmental & road type multipliers (Highway, Rain, Speed limit)
                  |
                  +---> [5] Historical Deterioration Monitor (backend/progress_monitor.py)
                  |         - Temporal baseline vs post-repair comparison
                  |         - Side-by-side composite visual evidence generation
                  |
                  +---> [6] Multi-Format Report Generator (backend/report_generator.py)
                            - Executive Printable HTML, Tabular CSV, and Structured JSON
```

### Components & Technologies:
- **Object Detection & Segmentation**: YOLOv8m (RDD2022 multi-country road damage model) + fine-tuned high-recall pothole cavity specialist (`roadvision_finetuned_v2.pt`) + YOLOv8s Instance Segmentation.
- **Backend**: FastAPI, SQLAlchemy ORM, SQLite (`data/roadvision.db`), OpenCV, NumPy, SciPy.
- **Frontend**: Responsive dashboard with Tailwind CSS, Chart.js, Leaflet GIS map with CartoDB dark basemap, and Lucide icons.

---

## 2. Core Expected Features Matrix

| Feature | Implementation Details | File References |
|---|---|---|
| **Image & Video Upload** | Asynchronous drag-and-drop dropzones with client-side preview and progress indicators. Handles high-res photos and video clips. | `frontend/templates/index.html`<br>`frontend/static/js/app.js` |
| **Damage Categories** | Detects standard RDD2022 surface distresses:<br>• **D00**: Longitudinal Crack<br>• **D10**: Transverse Crack<br>• **D20**: Alligator / Fatigue Crack<br>• **D40**: Pothole Cavity | `backend/config.py`<br>`backend/detector.py` |
| **BBoxes & Segmentation Masks** | Color-coded bounding boxes and alpha-blended polygon segmentation overlays indicating precise distress geometries. | `backend/detector.py` |
| **Severity Classification** | Classified into **Minor**, **Moderate**, and **Severe** based on relative surface area coverage ($A_{\text{defect}} / A_{\text{image}}$), aspect ratio, and estimated cavity depth tier. | `backend/config.py` |
| **Location Metadata** | Automatic extraction of EXIF GPS tags (latitude, longitude, altitude) from survey photos with manual fallback and spatial mapping. | `backend/detector.py` |
| **Damage Reports** | Automated one-click export into three formats:<br>1. **Executive Printable HTML** (formal engineering layout)<br>2. **Tabular CSV** (raw defect inventory)<br>3. **Structured JSON** (GIS & enterprise integration) | `backend/report_generator.py` |
| **Dashboard & Inventory** | Executive dashboard displaying total inspections, defect breakdowns by category, severity distributions, and a searchable survey records table. | `frontend/templates/index.html` |

---

## 3. Mandatory Advanced Features

### 1. Unique Pothole Tracking (Video Frames)
- **Problem**: In continuous dashcam or drone video, a vehicle moves past a pothole over 15–40 frames. A naive detector counts that single defect 40 times.
- **Implementation** (`backend/tracker.py`):
  1. Implements a **ByteTrack Centroid-IoU Association Engine**.
  2. Computes bounding box spatial overlap ($\text{IoU} \ge 0.25$) and Euclidean centroid distance ($\Delta d \le 85\text{ px}$) between consecutive frames.
  3. Binds detections to persistent tracking identities (`POTHOLE-001`, `CRACK-002`).
  4. Tracks lifetime metrics: first frame, last frame, track duration, and peak classification confidence.
  5. Renders an annotated MP4 video with a heads-up telemetry HUD showing live frame number, active defect count, and bounding box trackers.

### 2. Duplicate Report Detection
- **Problem**: Citizens and municipal inspectors frequently report the same road hazard multiple times, inflating backlogs.
- **Implementation** (`backend/duplicate_engine.py`):
  1. **Spatial Proximity**: Calculates Great-Circle Haversine distance between incoming defect coordinates and all existing active defects. Candidates within **25 meters** are flagged.
  2. **Perceptual Visual Hashing (dHash)**: Computes a 64-bit difference hash over the grayscale defect region:
     $$\text{Visual Similarity} = \left(1.0 - \frac{\text{Hamming Distance}}{64}\right) \times 100\%$$
  3. Matches with $\ge 75\%$ similarity are linked as duplicates with a status of `Pending`.
  4. Administrators can review spatial proximity and visual similarity on the **Duplicate Engine** tab and click **"Confirm & Merge Duplicate"** or **"Dismiss"**.

### 3. Road Damage Risk Prediction
- **Problem**: Equal-sized potholes pose vastly different risks on a 90 km/h wet highway versus a 30 km/h dry residential alley.
- **Implementation** (`backend/risk_engine.py`):
  $$\text{Base Score} = \sum (\text{Severity Base} \times \text{Category Weight})$$
  $$\text{Risk Score} = \min\left(100.0, \, \text{Base Score} \times F_{\text{density}} \times M_{\text{road}} \times M_{\text{speed}} \times M_{\text{weather}} \times M_{\text{traffic}}\right)$$
  - **Category Weight**: Pothole D40 (1.5x) > Alligator D20 (1.3x) > Longitudinal/Transverse (1.0x).
  - **Road Classification**: Highway (1.4x) > Arterial (1.2x) > Local (1.0x) > Residential (0.9x).
  - **Speed Limit Factor**: $M_{\text{speed}} = 1.0 + (\text{Speed Limit} - 40) \times 0.005$.
  - **Weather**: Rainy/Wet (1.3x) > Fog/Night (1.2x) > Clear/Dry (1.0x).
  - Categorizes risk into **Low (0–25)**, **Moderate (26–50)**, **High (51–75)**, and **Critical (76–100)** with human-readable contributing factor explanations.

### 4. Manual Verification & Correction Portal
- **Problem**: AI models can generate false positives (shadows, oil spills, paver joints). Civil authorities require human-in-the-loop oversight before allocating repair budgets.
- **Implementation** (`frontend/templates/index.html#verification`, `backend/app.py`):
  - Table of all unverified AI detections with defect thumbnail, track ID, confidence, and location.
  - One-click **"Approve"** (marks as Verified).
  - One-click **"Reject False Positive"** (purges or archives detection).
  - Modal to adjust category classification or alter severity tier.
  - Every action writes an immutable record to the `audit_logs` table recording reviewer name, timestamp, and modification notes via `/api/defects/{id}/verify`.

### 5. Road Damage Progress Monitoring
- **Problem**: Municipalities need to verify whether road conditions are deteriorating over time or whether contractor repairs met compliance standards.
- **Implementation** (`backend/progress_monitor.py`):
  1. Compares baseline survey ($T_1$) with follow-up survey ($T_2$) at the same road corridor.
  2. Calculates delta in defect count ($\Delta N$) and damaged surface area ($\Delta A\%$).
  3. Classifies trend into three deterministic states:
     - **"Repaired / Improved"**: Total defects eliminated or distress area reduced by $> 25\%$.
     - **"Stable"**: Defect count and area change within $\pm 10\%$.
     - **"Worsened"**: New defects formed or existing cracks propagated into potholes.
  4. Synthesizes a side-by-side composite visual evidence image comparing before-and-after conditions with a trend banner.

---

## 4. Empirical AI Model Benchmark & Evaluation

Evaluated across candidate architectures on CPU hardware (`MODEL_BENCHMARK_REPORT.md` / `/api/models/benchmark`):

| Model Configuration | Target Classes | Precision | Recall | F1-Score | mAP@50 | Latency (CPU) | FPS | Role in System |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **YOLOv8m-RDD2022** | D00, D10, D20, D40 | 100.0% | 20.0% | 0.3333 | 0.5700 | 480 ms | 2.1 | Primary 4-Class Crack Model |
| **YOLOv8s Pothole Specialist** | Pothole | 75.0% | 60.0% | 0.6667 | 0.7100 | 112 ms | 8.9 | Pretrained Cavity Base |
| **Fine-Tuned Checkpoint (`roadvision_finetuned_v2.pt`)** | Potholes + Cracks | **90.6%** | **60.0%** | **0.7222** | **0.7908** | **119 ms** | **8.4** | **Deployed High-Recall Specialist** |
| **Multi-Model Ensemble (Integrated)** | All 4 Classes | **91.8%** | **85.0%** | **0.8826** | **0.8240** | **145 ms** | **6.9** | **Production Ensemble Engine** |

### High-Recall Ensemble Architecture:
1. **Parallel Execution**: Both multi-class RDD detector and fine-tuned cavity detector run in parallel.
2. **IoU Non-Maximum Suppression (NMS)**: When both models detect the same pothole ($\text{IoU} \ge 0.38$), the higher-confidence box is retained; unique detections from either model are preserved, raising recall to $\approx 85\%$.
3. **Temporal Multi-Frame Voting**: Persistent ByteTrack tracking prevents transient single-frame misses from dropping a defect.

---

## 5. Verification & Test Suite Summary

All 25 automated unit and integration tests pass without failure:
- `tests/test_api.py` (7 tests): REST API endpoints, image upload, reporting, metrics.
- `tests/test_detector.py` (5 tests): Object detection, bounding box logic, severity thresholds, dHash computation.
- `tests/test_duplicate.py` (4 tests): Haversine distance, dHash visual similarity matching, duplicate thresholding.
- `tests/test_progress.py` (3 tests): Temporal progression, condition trend classification, side-by-side synthesis.
- `tests/test_risk.py` (4 tests): Multi-factor heuristic scoring, road type and weather multipliers.
- `tests/test_tracker.py` (2 tests): Centroid-IoU association, persistent track ID assignment.

---

## 6. Execution Instructions

1. **Start the Platform Server**:
   ```powershell
   python run_server.py
   ```
   *(Or run `run.bat`)*

2. **Access the Web Dashboard**:
   - URL: http://127.0.0.1:8000/
   - API Docs: http://127.0.0.1:8000/docs
