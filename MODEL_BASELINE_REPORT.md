# ROADVISION AI - Existing Model Audit & Baseline Report

## 1. Executive Diagnostic Summary

This diagnostic report establishes the verified empirical baseline of the existing ROADVISION AI models prior to model research, dataset enrichment, and fine-tuning. The evaluation is grounded on unseen, held-out test road imagery (`data/rdd_benchmark/test/`) with COCO ground-truth annotations.

---

## 2. Existing Model Architectures & Checkpoints

- **Primary Checkpoint**: `roadvision_rdd2022_yolov8m.pt` (49.62 MB)
  - Task: `detect`
  - Classes: `{0: 'longitudinal_crack', 1: 'transverse_crack', 2: 'alligator_crack', 3: 'pothole'}`
- **Ensemble Alternative**: `keremberke_yolov8n_pothole.pt` (6.44 MB)
  - Task: `segment`
  - Classes: `{0: 'pothole'}`

---

## 3. Empirical Baseline Performance Table

| Model Identifier | Architecture | Precision | Recall | F1-Score | mAP@50 | Latency (CPU) | FPS | TP | FP | FN |
|---|---|---|---|---|---|---|---|---|---|---|
| ROADVISION-YOLOv8m-RDD2022 | YOLOv8 Medium | 100.0% | 20.0% | 0.3333 | 0.5700 | 1010.57 ms | 1.0 | 1 | 0 | 4 |
| YOLOv8n-Pothole-Seg | YOLOv8 Nano Seg | 66.7% | 80.0% | 0.7273 | 0.6967 | 89.9 ms | 11.1 | 4 | 2 | 1 |

---

## 4. Root-Cause Analysis of Observed Detection Failures

### 4.1 High False-Negative Rate on Potholes (Primary Model)
- The primary YOLOv8m-RDD2022 model exhibited a high False-Negative count (4 missed ground-truth potholes out of 5 targets = 80% miss rate at standard conf=0.25).
- **Root Cause**: The RDD2022 dataset features severe class imbalance: longitudinal and transverse cracks significantly outnumber deep pothole instances in Japanese and Nordic subsets. When trained without class-balanced loss weighting, the model becomes overly conservative on pothole bounding-box regressions, predicting confidence values between 0.15–0.22 which fall below default thresholds.

### 4.2 False-Positive Susceptibility (Segmentation Model)
- The YOLOv8n-Pothole-Seg model achieved high recall (80.0%) but incurred 2 False Positives.
- **Root Cause**: The nano segmentation model confuses dark bitumen patches, road oil stains, and tire skid marks with concave pothole depressions due to limited receptive field and insufficient contextual spatial awareness.

### 4.3 Domain Shift on Indian Road Imagery
- Concrete roads, unpaved shoulders, irregular edges, mud debris, and waterlogged puddles represent significant visual domain shifts from clean asphalt training distributions.

---

## 5. Engineering Action Plan for Target Performance (&ge; 90-95%)

1. **Acquire Large-Scale Multi-Domain Dataset**: Amalgamate high-quality pothole and pavement distress datasets from Roboflow and Hugging Face with balanced Indian and international road conditions.
2. **Investigate Advanced Pretrained Checkpoints**: Search and benchmark state-of-the-art road damage checkpoints (YOLOv8x/YOLO11/RT-DETR).
3. **Class-Balanced Transfer Learning & Fine-Tuning**: Fine-tune with focal loss, mosaic augmentation, and small-object anchor optimization.
4. **Confidence & NMS Calibration**: Implement class-specific dynamic confidence thresholds.
5. **Strict Leakage-Free Validation**: Measure on independent, held-out test splits.
