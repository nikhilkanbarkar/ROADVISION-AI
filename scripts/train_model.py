"""
ROADVISION AI - Phase 5: Advanced Model Training and Fine-Tuning Pipeline
Fine-tunes the road damage detection model on the prepared multi-domain dataset
using transfer learning from the best pretrained checkpoint.
"""
import os
import sys
import time
import json
from ultralytics import YOLO

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_YAML = os.path.join(ROOT_DIR, "data", "yolo_dataset", "data.yaml")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
BASE_WEIGHTS = os.path.join(MODELS_DIR, "alternative", "harisanth_yolov8_pothole.pt")
RUNS_DIR = os.path.join(MODELS_DIR, "training")

def train():
    print("=" * 60)
    print("  ROADVISION AI - FINE-TUNING & TRANSFER LEARNING")
    print("=" * 60)
    print(f"Data YAML: {DATA_YAML}")
    print(f"Base Weights: {BASE_WEIGHTS}")

    # Use pretrained Harisanth Pothole detection model or standard YOLOv8s
    model = YOLO(BASE_WEIGHTS)
    print("Loaded base pretrained checkpoint.")

    t0 = time.time()
    # Train for 5 epochs on CPU with optimized batch size and data augmentation
    results = model.train(
        data=DATA_YAML,
        epochs=5,
        imgsz=512,
        batch=8,
        device="cpu",
        workers=2,
        project=RUNS_DIR,
        name="roadvision_finetuned",
        exist_ok=True,
        verbose=True,
        mosaic=0.5,
        mixup=0.1,
        patience=5,
        plots=True
    )
    duration = time.time() - t0
    print(f"\n[Training] Completed in {duration:.1f} seconds ({duration/60:.2f} mins)!")

    # Check best model location
    best_pt = os.path.join(RUNS_DIR, "roadvision_finetuned", "weights", "best.pt")
    if os.path.exists(best_pt):
        print(f"Best fine-tuned model saved to: {best_pt} ({os.path.getsize(best_pt)/(1024*1024):.2f} MB)")
    else:
        print(f"Warning: best.pt not found at expected path: {best_pt}")

    # Write MODEL_TRAINING_REPORT.md
    report_path = os.path.join(ROOT_DIR, "MODEL_TRAINING_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ROADVISION AI - Model Fine-Tuning and Optimization Report\n\n")
        f.write("## 1. Training Overview\n\n")
        f.write("- **Architecture**: YOLOv8 Small (`yolov8s`)\n")
        f.write(f"- **Initial Checkpoint**: `{os.path.basename(BASE_WEIGHTS)}` (Pothole Pretrained Checkpoint)\n")
        f.write(f"- **Dataset**: Calibrated Road Damage Dataset (80 train, 5 val, 5 test images)\n")
        f.write("- **Hardware Target**: Intel Core / AMD 6-Core Physical / 12 Logical CPU Threads\n")
        f.write("- **Batch Size**: 8\n")
        f.write("- **Input Resolution**: 512 &times; 512 pixels\n")
        f.write("- **Epochs**: 5\n")
        f.write(f"- **Training Duration**: {duration:.1f} seconds\n")
        f.write("- **Augmentation**: Mosaic (0.5), Mixup (0.1), Horizontal Flip, HSV Color Perturbation\n\n")
        f.write("---\n\n")
        f.write("## 2. Checkpoint Artifacts\n\n")
        f.write(f"- **Best Weights**: `models/training/roadvision_finetuned/weights/best.pt`\n")
        f.write(f"- **Last Weights**: `models/training/roadvision_finetuned/weights/last.pt`\n")
        f.write("- **Optimization Curves**: Saved in `models/training/roadvision_finetuned/`\n")

    print(f"Report written to {report_path}")

if __name__ == "__main__":
    train()
