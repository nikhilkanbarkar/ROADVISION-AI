"""
ROADVISION AI - Production Computer Vision & Multi-Model Road Damage Detection Engine
Combines high-recall pothole models, RDD2022 multi-class defect recognition (D00, D10, D20, D40),
instance segmentation, EXIF GPS extraction, severity classification, and perceptual hashing.
"""
import os
import cv2
import numpy as np
from PIL import Image, ExifTags
from ultralytics import YOLO

from backend.config import (
    PRIMARY_MODEL_PATH,
    ALTERNATIVE_MODEL_PATH,
    FAST_MODEL_PATH,
    FINETUNED_MODEL_PATH,
    RDD_CLASSES,
    SEVERITY_THRESHOLDS,
    MODELS_DIR
)

def compute_dhash(img_np, hash_size=8):
    """Computes a 64-bit difference hash (dHash) from a numpy BGR or grayscale image."""
    try:
        if len(img_np.shape) == 3:
            gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_np
        resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
        diff = resized[:, 1:] > resized[:, :-1]
        hash_val = sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])
        return f"{hash_val:016x}"
    except Exception:
        return "0000000000000000"

def extract_exif_gps(image_path):
    """Extracts GPS Latitude and Longitude from EXIF metadata if present."""
    if not isinstance(image_path, str) or not os.path.exists(image_path):
        return None, None
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        if not exif:
            return None, None

        gps_info = {}
        for tag, value in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in value:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = value[t]

        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = gps_info["GPSLatitude"]
            lat_ref = gps_info.get("GPSLatitudeRef", "N")
            lon = gps_info["GPSLongitude"]
            lon_ref = gps_info.get("GPSLongitudeRef", "E")

            def to_deg(dms):
                return float(dms[0]) + float(dms[1])/60.0 + float(dms[2])/3600.0

            lat_val = to_deg(lat)
            if lat_ref == "S":
                lat_val = -lat_val

            lon_val = to_deg(lon)
            if lon_ref == "W":
                lon_val = -lon_val

            return round(lat_val, 6), round(lon_val, 6)
    except Exception:
        pass
    return None, None

def compute_box_iou(box1, box2):
    """Calculates Intersection over Union between two bounding boxes [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area

class RoadVisionDetector:
    def __init__(
        self,
        primary_path=PRIMARY_MODEL_PATH,
        finetuned_path=FINETUNED_MODEL_PATH,
        alt_path=ALTERNATIVE_MODEL_PATH
    ):
        self.primary_path = primary_path
        self.finetuned_path = finetuned_path
        self.alt_path = alt_path

        self.primary_model = None
        self.pothole_model = None
        self.alt_model = None

        self._load_models()

    def _load_models(self):
        # 1. Primary RDD2022 Multi-Class Model (D00, D10, D20, D40)
        if os.path.exists(self.primary_path):
            try:
                self.primary_model = YOLO(self.primary_path)
                print(f"[Detector] Loaded Primary RDD2022 Model: {os.path.basename(self.primary_path)}")
            except Exception as e:
                print(f"[Detector] Error loading primary model: {e}")

        # 2. High-Recall Specialized Pothole Model (Fine-tuned / Harisanth weights)
        candidate_pothole_paths = [
            self.finetuned_path,
            os.path.join(MODELS_DIR, "training", "roadvision_finetuned", "weights", "best.pt"),
            os.path.join(MODELS_DIR, "alternative", "harisanth_yolov8_pothole.pt"),
            os.path.join(MODELS_DIR, "alternative", "rohith_yolov8_pothole.pt")
        ]
        for p in candidate_pothole_paths:
            if os.path.exists(p):
                try:
                    self.pothole_model = YOLO(p)
                    print(f"[Detector] Loaded High-Recall Pothole Specialist: {os.path.basename(p)}")
                    break
                except Exception as e:
                    print(f"[Detector] Failed loading pothole model from {p}: {e}")

        # 3. Instance Segmentation Model
        if os.path.exists(self.alt_path):
            try:
                self.alt_model = YOLO(self.alt_path)
                print(f"[Detector] Loaded Segmentation Model: {os.path.basename(self.alt_path)}")
            except Exception as e:
                print(f"[Detector] Error loading alt model: {e}")

    def classify_severity(self, class_name, relative_area):
        """Calculates severity (Minor, Moderate, Severe) based on defect class and relative area."""
        cls_lower = class_name.lower()
        if "pothole" in cls_lower:
            if relative_area >= 0.040:
                return "Severe", "Deep"
            elif relative_area >= 0.015:
                return "Moderate", "Medium"
            else:
                return "Minor", "Shallow"
        elif "alligator" in cls_lower:
            if relative_area >= 0.080:
                return "Severe", "Deep"
            elif relative_area >= 0.030:
                return "Moderate", "Medium"
            else:
                return "Minor", "Shallow"
        else: # Longitudinal / Transverse cracks
            if relative_area >= 0.070:
                return "Severe", "Medium"
            elif relative_area >= 0.025:
                return "Moderate", "Shallow"
            else:
                return "Minor", "Shallow"

    def detect_image(self, source, conf_thresh=0.15, iou_thresh=0.45, model_choice="ensemble", imgsz=640):
        """
        Runs road damage detection on an image path or numpy BGR frame.
        Supports multi-model ensemble merging to ensure all potholes and cracks are detected.
        """
        lat, lon = None, None

        if isinstance(source, str):
            if not os.path.exists(source):
                raise FileNotFoundError(f"Image not found at {source}")
            img_bgr = cv2.imread(source)
            if img_bgr is None:
                raise ValueError(f"Failed to read image at {source}")
            lat, lon = extract_exif_gps(source)
        elif isinstance(source, np.ndarray):
            img_bgr = source.copy()
        else:
            raise TypeError("Source must be either an image file path string or a numpy array.")

        img_h, img_w = img_bgr.shape[:2]
        total_pixels = img_h * img_w

        # Accumulate candidate detections from all relevant models
        candidate_boxes = [] # Each: {bbox, conf, class_id, class_name, category_code, display_name}

        # 1. Query Pothole Specialist Model (High recall on real road cavities)
        if self.pothole_model is not None and model_choice in ["ensemble", "finetuned", "primary"]:
            try:
                pothole_res = self.pothole_model.predict(
                    source=img_bgr,
                    conf=max(0.10, conf_thresh - 0.03), # slightly sensitive to catch distant/small holes
                    iou=iou_thresh,
                    imgsz=imgsz,
                    verbose=False
                )[0]
                for b in pothole_res.boxes:
                    conf = float(b.conf[0].item())
                    xyxy = [int(v) for v in b.xyxy[0].tolist()]
                    candidate_boxes.append({
                        "bbox": xyxy,
                        "conf": conf,
                        "class_id": 3,
                        "class_name": "pothole",
                        "category_code": "D40",
                        "display_name": "Pothole",
                        "model_src": "pothole_specialist"
                    })
            except Exception as e:
                print(f"[Detector] Pothole model inference warning: {e}")

        # 2. Query Primary RDD2022 Multi-Class Model (Cracks D00, D10, D20, and D40)
        if self.primary_model is not None and model_choice in ["ensemble", "primary"]:
            try:
                primary_res = self.primary_model.predict(
                    source=img_bgr,
                    conf=conf_thresh,
                    iou=iou_thresh,
                    imgsz=imgsz,
                    verbose=False
                )[0]
                for b in primary_res.boxes:
                    cls_id = int(b.cls[0].item())
                    raw_cls_name = self.primary_model.names.get(cls_id, f"class_{cls_id}").lower()
                    conf = float(b.conf[0].item())
                    xyxy = [int(v) for v in b.xyxy[0].tolist()]

                    cat_code = "D40"
                    display_name = "Pothole"
                    if "longitudinal" in raw_cls_name:
                        cat_code, display_name = "D00", "Longitudinal Crack"
                    elif "transverse" in raw_cls_name:
                        cat_code, display_name = "D10", "Transverse Crack"
                    elif "alligator" in raw_cls_name:
                        cat_code, display_name = "D20", "Alligator Crack"

                    candidate_boxes.append({
                        "bbox": xyxy,
                        "conf": conf,
                        "class_id": cls_id,
                        "class_name": raw_cls_name,
                        "category_code": cat_code,
                        "display_name": display_name,
                        "model_src": "rdd2022"
                    })
            except Exception as e:
                print(f"[Detector] Primary model inference warning: {e}")

        # 3. Query Instance Segmentation Model (if selected or fallback)
        if self.alt_model is not None and (model_choice == "segmentation" or (model_choice == "ensemble" and len(candidate_boxes) == 0)):
            try:
                alt_res = self.alt_model.predict(
                    source=img_bgr,
                    conf=conf_thresh,
                    iou=iou_thresh,
                    verbose=False
                )[0]
                for b in alt_res.boxes:
                    conf = float(b.conf[0].item())
                    xyxy = [int(v) for v in b.xyxy[0].tolist()]
                    candidate_boxes.append({
                        "bbox": xyxy,
                        "conf": conf,
                        "class_id": 3,
                        "class_name": "pothole",
                        "category_code": "D40",
                        "display_name": "Pothole",
                        "model_src": "segmentation"
                    })
            except Exception as e:
                print(f"[Detector] Alt model inference warning: {e}")

        # Fallback if no models loaded
        if not candidate_boxes and self.primary_model is None and self.pothole_model is None:
            return img_bgr, [], (lat, lon)

        # 4. Non-Maximum Suppression (NMS) Merging across models
        # Sort candidates by confidence descending
        candidate_boxes.sort(key=lambda x: x["conf"], reverse=True)
        final_boxes = []

        for cand in candidate_boxes:
            c_box = cand["bbox"]
            is_duplicate = False

            for existing in final_boxes:
                e_box = existing["bbox"]
                overlap = compute_box_iou(c_box, e_box)
                # If high overlap, keep the existing higher-confidence detection
                if overlap >= 0.38:
                    is_duplicate = True
                    # If existing was generic crack but candidate has strong pothole confidence, upgrade to Pothole
                    if existing["category_code"] != "D40" and cand["category_code"] == "D40" and cand["conf"] >= existing["conf"]:
                        existing["category_code"] = "D40"
                        existing["display_name"] = "Pothole"
                        existing["conf"] = cand["conf"]
                    break

            if not is_duplicate:
                final_boxes.append(cand)

        # 5. Format detections, calculate severity, image hashes, and render annotations
        detections = []
        annotated = img_bgr.copy()
        defect_idx = 1

        for det_box in final_boxes:
            x1, y1, x2, y2 = det_box["bbox"]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_w - 1, x2), min(img_h - 1, y2)

            box_area = (x2 - x1) * (y2 - y1)
            rel_area = box_area / total_pixels if total_pixels > 0 else 0.0

            cat_code = det_box["category_code"]
            display_name = det_box["display_name"]
            conf = det_box["conf"]

            severity, depth_tier = self.classify_severity(display_name, rel_area)

            # Crop patch for perceptual hash
            crop = img_bgr[y1:y2, x1:x2]
            p_hash = compute_dhash(crop) if crop.size > 0 else "0000000000000000"

            track_id = f"{cat_code}-{defect_idx:03d}"
            defect_idx += 1

            det = {
                "track_id": track_id,
                "class_id": det_box["class_id"],
                "class_name": det_box["class_name"],
                "category_code": cat_code,
                "display_name": display_name,
                "confidence": round(conf, 3),
                "bbox": [x1, y1, x2, y2],
                "relative_area": round(rel_area, 4),
                "severity": severity,
                "depth_tier": depth_tier,
                "image_hash": p_hash,
                "latitude": lat,
                "longitude": lon
            }
            detections.append(det)

            # Visual overlay styling
            color = (59, 130, 246) # Blue for D00
            if cat_code == "D10":
                color = (16, 185, 129) # Green
            elif cat_code == "D20":
                color = (245, 158, 11) # Orange/Amber
            elif cat_code == "D40":
                color = (239, 68, 68) # Red for Pothole

            # Semi-transparent fill
            overlay = annotated.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.20, annotated, 0.80, 0, annotated)

            # Solid border
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)

            # Label badge
            label = f"{display_name} {conf*100:.0f}% [{severity}]"
            font_scale = 0.4
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            badge_y1 = max(0, y1 - th - 6)
            cv2.rectangle(annotated, (x1, badge_y1), (x1 + tw + 8, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 4, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        return annotated, detections, (lat, lon)

# Singleton instance
detector = RoadVisionDetector()
