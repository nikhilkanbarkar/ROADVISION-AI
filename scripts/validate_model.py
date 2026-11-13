"""
ROADVISION AI - Model Validation Script
Tests the primary YOLOv8m RDD2022 model on sample road imagery.
"""
import os
import sys
import numpy as np
import cv2
from ultralytics import YOLO

PRIMARY_MODEL = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "primary", "roadvision_rdd2022_yolov8m.pt")

def create_sample_road_image(path):
    """Creates a realistic synthetic asphalt road image with pothole and cracks for validation."""
    h, w = 640, 640
    # Asphalt base color
    img = np.full((h, w, 3), 60, dtype=np.uint8)
    # Add asphalt noise
    noise = np.random.normal(0, 12, (h, w, 3)).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Road marking
    cv2.line(img, (320, 0), (320, 200), (220, 220, 220), 8)
    cv2.line(img, (320, 300), (320, 500), (220, 220, 220), 8)

    # Draw dark irregular pothole depression
    cv2.ellipse(img, (240, 360), (70, 45), 20, 0, 360, (20, 20, 22), -1)
    cv2.ellipse(img, (235, 355), (55, 35), 20, 0, 360, (10, 10, 12), -1)
    # Pothole jagged edges
    pts = np.array([[180, 340], [220, 320], [280, 330], [310, 370], [270, 410], [200, 400], [170, 370]], np.int32)
    cv2.polylines(img, [pts], True, (15, 15, 18), 4)

    # Draw longitudinal crack
    crack_pts = np.array([[420, 100], [430, 220], [425, 350], [440, 480], [435, 590]], np.int32)
    cv2.polylines(img, [crack_pts], False, (18, 18, 20), 3)

    # Draw transverse crack
    cv2.line(img, (80, 180), (380, 200), (22, 22, 25), 3)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, img)
    return path

def validate():
    print(f"Loading primary model from: {PRIMARY_MODEL}")
    if not os.path.exists(PRIMARY_MODEL):
        print(f"ERROR: Model file not found at {PRIMARY_MODEL}")
        return False

    model = YOLO(PRIMARY_MODEL)
    print("Model loaded successfully!")
    print(f"Classes: {model.names}")

    test_img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads", "validation_sample.jpg")
    create_sample_road_image(test_img_path)
    print(f"Generated validation sample image at {test_img_path}")

    results = model.predict(source=test_img_path, conf=0.15, verbose=True)
    res = results[0]

    print(f"Detections count: {len(res.boxes)}")
    for i, box in enumerate(res.boxes):
        cls_id = int(box.cls[0].item())
        cls_name = model.names[cls_id]
        conf = float(box.conf[0].item())
        xyxy = [round(x, 2) for x in box.xyxy[0].tolist()]
        print(f"  [{i+1}] Class: {cls_name} (ID: {cls_id}), Conf: {conf:.3f}, BBox: {xyxy}")

    # Save output visualization
    annotated = res.plot()
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "outputs", "validation_result.jpg")
    cv2.imwrite(out_path, annotated)
    print(f"Saved annotated validation result to {out_path}")
    return True

if __name__ == "__main__":
    validate()
