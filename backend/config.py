"""
ROADVISION AI - Global Configuration and System Constants
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Storage paths
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
BENCHMARK_DIR = os.path.join(DATA_DIR, "rdd_benchmark")

# Models paths
MODELS_DIR = os.path.join(BASE_DIR, "models")
PRIMARY_MODEL_PATH = os.path.join(MODELS_DIR, "primary", "roadvision_rdd2022_yolov8m.pt")
FINETUNED_MODEL_PATH = os.path.join(MODELS_DIR, "primary", "roadvision_finetuned_v2.pt")
ALTERNATIVE_MODEL_PATH = os.path.join(MODELS_DIR, "alternative", "keremberke_yolov8s_pothole_seg.pt")
FAST_MODEL_PATH = os.path.join(MODELS_DIR, "alternative", "dronefreak_rdd2022_yolov8s.pt")

# Database path
DB_PATH = os.path.join(DATA_DIR, "roadvision.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Ensure directories exist
for d in [DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, REPORTS_DIR, BENCHMARK_DIR, MODELS_DIR]:
    os.makedirs(d, exist_ok=True)

# RDD2022 Class Mappings
RDD_CLASSES = {
    0: {"code": "D00", "name": "longitudinal_crack", "display": "Longitudinal Crack", "color": "#3B82F6", "weight": 1.2},
    1: {"code": "D10", "name": "transverse_crack", "display": "Transverse Crack", "color": "#10B981", "weight": 1.1},
    2: {"code": "D20", "name": "alligator_crack", "display": "Alligator Crack", "color": "#F59E0B", "weight": 1.6},
    3: {"code": "D40", "name": "pothole", "display": "Pothole", "color": "#EF4444", "weight": 2.2}
}

# Severity Thresholds (Based on relative bbox area to image area)
SEVERITY_THRESHOLDS = {
    "minor": 0.015,     # < 1.5% of image area
    "moderate": 0.050,  # 1.5% - 5.0%
    "severe": 0.050     # > 5.0%
}

# Duplicate Detection Thresholds
DUPLICATE_GPS_RADIUS_METERS = 25.0
DUPLICATE_VISUAL_SIMILARITY_MIN = 0.75

# Risk Assessment Weightings
RISK_WEIGHTS = {
    "severity": {"Minor": 10, "Moderate": 25, "Severe": 45},
    "category": {"D40": 1.5, "D20": 1.3, "D00": 1.0, "D10": 1.0},
    "road_class": {"Highway": 1.4, "Arterial": 1.2, "Local": 1.0, "Residential": 0.9},
    "weather": {"Rainy/Wet": 1.3, "Clear/Dry": 1.0, "Fog/Night": 1.2}
}

# Server Config
HOST = "127.0.0.1"
PORT = 8000
API_PREFIX = "/api"
