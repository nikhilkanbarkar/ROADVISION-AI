"""
ROADVISION AI - Test Suite for AI Detection Engine
Tests model loading, class mapping, inference, severity, and edge cases.
"""
import os
import pytest
import numpy as np
import cv2
from backend.detector import RoadVisionDetector, compute_dhash, extract_exif_gps
from backend.config import PRIMARY_MODEL_PATH, ALTERNATIVE_MODEL_PATH

def test_detector_initialization():
    detector = RoadVisionDetector(primary_path=PRIMARY_MODEL_PATH, alt_path=ALTERNATIVE_MODEL_PATH)
    assert detector.primary_model is not None, "Primary model failed to load"
    assert "longitudinal_crack" in detector.primary_model.names.values()
    assert "pothole" in detector.primary_model.names.values()

def test_severity_classification():
    det = RoadVisionDetector()
    # Pothole large relative area
    sev, depth = det.classify_severity("Pothole", 0.055)
    assert sev == "Severe"
    assert depth == "Deep"

    # Pothole small relative area
    sev, depth = det.classify_severity("Pothole", 0.010)
    assert sev == "Minor"
    assert depth == "Shallow"

    # Crack moderate
    sev, depth = det.classify_severity("Longitudinal Crack", 0.040)
    assert sev == "Moderate"

def test_perceptual_dhash():
    img1 = np.full((100, 100, 3), 120, dtype=np.uint8)
    h1 = compute_dhash(img1)
    assert isinstance(h1, str)
    assert len(h1) == 16

    # Similar images produce identical or low Hamming distance hashes
    img2 = np.full((100, 100, 3), 122, dtype=np.uint8)
    h2 = compute_dhash(img2)
    assert h1 == h2

def test_image_inference_real_file(tmp_path):
    img = np.full((320, 320, 3), 70, dtype=np.uint8)
    cv2.circle(img, (160, 160), 40, (20, 20, 20), -1)
    test_path = str(tmp_path / "test_road.jpg")
    cv2.imwrite(test_path, img)

    detector = RoadVisionDetector()
    annotated, dets, (lat, lon) = detector.detect_image(test_path, conf_thresh=0.05)
    assert isinstance(annotated, np.ndarray)
    assert isinstance(dets, list)

def test_missing_image_handling():
    detector = RoadVisionDetector()
    with pytest.raises(FileNotFoundError):
        detector.detect_image("non_existent_image_path_12345.jpg")
