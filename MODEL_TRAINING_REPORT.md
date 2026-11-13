# ROADVISION AI - Model Fine-Tuning and Optimization Report

## 1. Training Overview

- **Architecture**: YOLOv8 Small (`yolov8s`)
- **Initial Checkpoint**: `harisanth_yolov8_pothole.pt` (Pothole Pretrained Checkpoint)
- **Dataset**: Calibrated Road Damage Dataset (80 train, 5 val, 5 test images)
- **Hardware Target**: Intel Core / AMD 6-Core Physical / 12 Logical CPU Threads
- **Batch Size**: 8
- **Input Resolution**: 512 &times; 512 pixels
- **Epochs**: 5
- **Training Duration**: 375.1 seconds
- **Augmentation**: Mosaic (0.5), Mixup (0.1), Horizontal Flip, HSV Color Perturbation

---

## 2. Checkpoint Artifacts

- **Best Weights**: `models/training/roadvision_finetuned/weights/best.pt`
- **Last Weights**: `models/training/roadvision_finetuned/weights/last.pt`
- **Optimization Curves**: Saved in `models/training/roadvision_finetuned/`
