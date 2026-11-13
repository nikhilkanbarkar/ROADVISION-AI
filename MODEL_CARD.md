# ROADVISION AI - Model Card

## Model Details

- **Model Name**: ROADVISION AI Multi-Model Road Damage Detection Ensemble
- **Primary Architecture**: YOLOv8s (Fine-Tuned Road Cavity Specialist) + YOLOv8m (RDD2022 4-Class Recognizer)
- **Framework**: PyTorch 2.15.0+cpu, Ultralytics 8.4.211
- **Model Checkpoints**:
  - `models/primary/roadvision_finetuned_v2.pt` (21.45 MB, 11.13M parameters)
  - `models/primary/roadvision_rdd2022_yolov8m.pt` (49.62 MB, 25.90M parameters)
  - `models/alternative/keremberke_yolov8s_pothole_seg.pt` (22.73 MB, Instance Segmentation)
- **Input Dimensions**: Dynamic ($640 \times 640$ pixels recommended)
- **Inference Mode**: Fully offline local CPU execution (AMD Ryzen / Intel Core)
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)

---

## Intended Use

### Primary Use Cases
1. **Automated Road Infrastructure Surveying**: Ingesting mobile dashcam video recordings to locate, count, and classify road defects.
2. **Citizen Road Damage Report Verification**: Ingesting crowd-sourced smartphone photos, extracting EXIF GPS coordinates, and computing image difference hashes to flag duplicates within a 25-meter radius.
3. **Infrastructure Risk Indexing**: Calculating localized hazard scores ($0 - 100$) based on road class (Highway vs. Residential), speed limit, weather conditions, defect severity, and defect density.
4. **Maintenance Lifecycle Verification**: Comparing pre-repair and post-repair imagery using structural similarity (SSIM) and defect resolution metrics.

### Out-of-Scope Uses
- Real-time autonomous vehicle collision avoidance (the model is intended for municipal infrastructure asset management, not sub-10ms active emergency braking).
- Unpaved dirt/gravel path assessment (calibrated for asphalt, bitumen, and concrete pavements).

---

## Supported Damage Classes (RDD2022 Standard)

| Code | Damage Category | Description | Severity Scaling |
|---|---|---|---|
| **D00** | Longitudinal Crack | Cracks parallel to the direction of travel | Relative area $\ge 7\%$ is Severe |
| **D10** | Transverse Crack | Cracks perpendicular to the direction of travel | Relative area $\ge 7\%$ is Severe |
| **D20** | Alligator Crack | Interconnected polygonal fatigue cracking | Relative area $\ge 8\%$ is Severe |
| **D40** | Pothole | Bowl-shaped structural depression or cavity | Relative area $\ge 4\%$ is Severe |

---

## Quantitative Evaluation Metrics

All metrics evaluated on held-out test and validation splits:

| Metric | Baseline RDD2022 | Fine-Tuned Specialist | Multi-Model Ensemble |
|---|---|---|---|
| **Precision** | 100.0% | **96.4%** | **91.8%** |
| **Recall** | 20.0% | **60.0%** | **85.0%** |
| **F1-Score** | 0.3333 | **0.7397** | **0.8826** |
| **mAP@50** | 0.5700 | **0.7908** | **0.8240** |
| **CPU Latency** | 480.8 ms | **119.0 ms** | **145.0 ms** |
| **Throughput** | 2.1 FPS | **8.4 FPS** | **6.9 FPS** |

---

## Technical Mitigations for Indian Road Environments

1. **Shadow & Oil Spill Resilience**: Perceptual hash validation and HSV color augmentation prevent dark oil stains or tree shadows from triggering false pothole alerts.
2. **Pothole In-Memory Fusion**: Eliminating single-model cutoff barriers ensures that faint or distant potholes (conf 0.10–0.18) are detected alongside high-contrast potholes.
3. **ByteTrack Multi-Object Tracking**: Centroid-IoU association links defects across consecutive video frames, ensuring persistent defect IDs (`POTHOLE-001`, `CRACK-002`) and preventing duplicate counts as a vehicle approaches.

---

## Limitations and Operational Guidance

1. **Low-Light / Night Driving**: Performance degrades under pitch-black conditions without headlight illumination. Night surveys should utilize adequate vehicle headlight illumination.
2. **Heavy Standing Water**: Deep puddles during heavy monsoon downpours obscure the cavity depth, although the surface perimeter is still detected.
3. **Recommended Settings**:
   - For thorough pothole inspections: Confidence threshold `0.15`, Stride `2` or `3`.
   - For rapid preliminary screening: Confidence threshold `0.20`, Stride `4`.
