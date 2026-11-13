# ROADVISION AI - Dataset Engineering & Quality Control Report

## 1. Dataset Provenance & Sources

The training, validation, and testing corpora were constructed by amalgamating verified road distress datasets:
1. **Kerem Berke Pothole Segmentation & Detection Benchmark** (Derived from Roboflow Universe)
2. **RDD2022 (Road Damage Detection 2022)** multi-country pavement distress imagery.
3. **Indian Road Conditions Calibration Subset** (waterlogged road cavities, broken asphalt borders, monsoon wear).

---

## 2. Dataset Partitioning & Leakage Prevention

| Split | Image Count | Bounding Box Annotations | Purpose |
|---|---|---|---|
| **Training (Train)** | 80 | 110 | Transfer learning and fine-tuning |
| **Validation (Val)** | 5 | 5 | Hyperparameter & threshold tuning |
| **Testing (Test)** | 5 | 5 | Independent, held-out evaluation |
| **Total Usable** | **90** | **120** | Full pipeline corpus |

---

## 3. Annotation Quality Control Audit

- **Zero-Area Boxes**: Automatically identified and pruned during COCO-to-YOLO normalization.
- **Boundary Clamping**: All coordinates verified within $[0.0, 1.0]$ image space bounds.
- **Data Leakage Mitigation**: Grouped by survey sequence; no identical or adjacent frame images appear across both training and testing splits.
