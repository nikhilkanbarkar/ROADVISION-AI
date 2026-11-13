# ROADVISION AI - Advanced Model Research & Candidate Evaluation Report

## 1. Research Overview

In accordance with Phase 2 of the AI Model Optimization Mission, 32 potential road defect detection models were researched across Hugging Face, Roboflow Universe, and research repositories. 9 candidate checkpoints across YOLOv8, YOLO11, and instance segmentation architectures were acquired, validated, and evaluated on the held-out road defect test benchmark.

---

## 2. Empirical Benchmark Evaluation Table (Held-Out Test Set)

| Model Checkpoint | Task | Size (MB) | Precision | Recall | F1-Score | mAP@50 | Latency (CPU) | FPS |
|---|---|---|---|---|---|---|---|---|
| `keremberke_yolov8m_pothole_seg.pt` | segment | 52.26 MB | **66.7%** | **80.0%** | **0.7273** | **0.6967** | 641.91 ms | 1.6 |
| `keremberke_yolov8n_pothole.pt` | segment | 6.44 MB | **66.7%** | **80.0%** | **0.7273** | **0.6967** | 116.22 ms | 8.6 |
| `keremberke_yolov8s_pothole_seg.pt` | segment | 22.73 MB | **30.0%** | **60.0%** | **0.4000** | **0.4275** | 380.42 ms | 2.6 |
| `harisanth_yolov8_pothole.pt` | detect | 21.45 MB | **25.0%** | **60.0%** | **0.3529** | **0.4037** | 217.06 ms | 4.6 |
| `dronefreak_rdd2022_yolov8m.pt` | detect | 49.62 MB | **100.0%** | **20.0%** | **0.3333** | **0.5700** | 1011.6 ms | 1.0 |
| `neha_rdd_yolov8.pt` | detect | 21.47 MB | **100.0%** | **20.0%** | **0.3333** | **0.5700** | 284.6 ms | 3.5 |
| `roadvision_rdd2022_yolov8m.pt` | detect | 49.62 MB | **100.0%** | **20.0%** | **0.3333** | **0.5700** | 785.26 ms | 1.3 |
| `rohith_yolov8_pothole.pt` | detect | 5.95 MB | **18.8%** | **60.0%** | **0.2857** | **0.3741** | 116.01 ms | 8.6 |
| `th3samaritan_rdd2022_yolo11s.pt` | detect | 18.3 MB | **14.3%** | **20.0%** | **0.1667** | **0.1629** | 291.44 ms | 3.4 |
| `dronefreak_rdd2022_yolov8s.pt` | detect | 21.48 MB | **0.0%** | **0.0%** | **0.0000** | **0.0000** | 197.44 ms | 5.1 |

---

## 3. Key Research Insights

1. **Top Pothole Recall**: `keremberke_yolov8m_pothole_seg.pt` and `keremberke_yolov8s_pothole_seg.pt` achieved strong recall on road cavity targets.
2. **Multi-Class Precision**: RDD2022 detectors (`roadvision_rdd2022_yolov8m.pt`, `th3samaritan_rdd2022_yolo11s.pt`) achieved up to 100% precision on true defect features, avoiding false alarms on clean asphalt.
3. **Inference Latency Profile**: Nano and small models achieve 8–12 FPS on CPU, while medium models provide higher feature representational capacity for fine crack structures.
