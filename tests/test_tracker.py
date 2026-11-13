"""
ROADVISION AI - Test Suite for Video Object Tracking Engine
Tests persistent ID assignment, trajectory tracking, and unique defect counting.
"""
import pytest
import numpy as np
from backend.tracker import VideoDamageTracker, TrackedDefect, compute_box_iou, _draw_track_overlay

def test_box_iou_calculation():
    box1 = [100, 100, 200, 200]
    box2 = [100, 100, 200, 200]
    assert compute_box_iou(box1, box2) == 1.0

    box3 = [300, 300, 400, 400]
    assert compute_box_iou(box1, box3) == 0.0

    box4 = [150, 100, 250, 200] # Half overlap
    iou = compute_box_iou(box1, box4)
    assert 0.30 <= iou <= 0.35

def test_persistent_unique_tracking():
    tracker = VideoDamageTracker(max_missed=5, iou_threshold=0.3)

    # Frame 1: Pothole appears at [100, 100, 180, 180]
    frame1_dets = [{
        "category_code": "D40",
        "class_name": "pothole",
        "display_name": "Pothole",
        "bbox": [100, 100, 180, 180],
        "confidence": 0.88,
        "severity": "Moderate"
    }]
    tracker.update_frame(frame1_dets, frame_idx=1, time_sec=0.04)
    assert len(tracker.active_tracks) == 1
    t1_id = tracker.active_tracks[0].track_id
    assert "POTHOLE" in t1_id

    # Frame 2: Same pothole slightly shifted at [102, 104, 182, 184]
    frame2_dets = [{
        "category_code": "D40",
        "class_name": "pothole",
        "display_name": "Pothole",
        "bbox": [102, 104, 182, 184],
        "confidence": 0.91,
        "severity": "Moderate"
    }]
    tracker.update_frame(frame2_dets, frame_idx=2, time_sec=0.08)
    assert len(tracker.active_tracks) == 1
    # Verify ID is preserved!
    assert tracker.active_tracks[0].track_id == t1_id
    assert tracker.active_tracks[0].detection_count == 2
    assert tracker.active_tracks[0].max_conf == 0.91

    # Frame 3: A NEW crack appears elsewhere [400, 50, 450, 300]
    frame3_dets = [
        {
            "category_code": "D40",
            "class_name": "pothole",
            "display_name": "Pothole",
            "bbox": [104, 108, 184, 188],
            "confidence": 0.89,
            "severity": "Moderate"
        },
        {
            "category_code": "D00",
            "class_name": "longitudinal_crack",
            "display_name": "Longitudinal Crack",
            "bbox": [400, 50, 450, 300],
            "confidence": 0.81,
            "severity": "Minor"
        }
    ]
    tracker.update_frame(frame3_dets, frame_idx=3, time_sec=0.12)
    assert len(tracker.active_tracks) == 2

    # Finalize
    all_tracks = tracker.finalize()
    assert len(all_tracks) == 2
    track_ids = [t.track_id for t in all_tracks]
    assert t1_id in track_ids


def test_video_track_overlay_draws_bounding_box():
    tracker = VideoDamageTracker()
    tracker.update_frame([{
        "category_code": "D40",
        "class_name": "pothole",
        "display_name": "Pothole",
        "bbox": [20, 30, 100, 90],
        "confidence": 0.9,
        "severity": "Moderate"
    }], frame_idx=1, time_sec=0.1)
    frame = np.zeros((120, 140, 3), dtype=np.uint8)

    _draw_track_overlay(frame, tracker.active_tracks[0])

    assert tuple(frame[30, 60]) == (0, 255, 255)
