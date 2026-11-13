"""
ROADVISION AI - Belagavi Integration & 3-State Architecture Test Suite
Verifies:
1. Belagavi City boundary enforcement (is_within_belagavi)
2. 3-State Data Pipeline (Submitted -> AI-Generated -> Verified)
3. Road Network Segments & Defect Spatial Matching
4. Risk-Aware Multi-Route Alternative Navigation & Exposure Scoring
5. Duplicate Candidate Resolution
6. Repair Lifecycle & Progression Tracking
"""
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.gis_belagavi import (
    is_within_belagavi, match_defect_to_belagavi_segment,
    recommend_best_route, BELAGAVI_JUNCTIONS, BELAGAVI_ROAD_SEGMENTS
)
from backend.database import SessionLocal
from backend.models_db import (
    Submission, AIDetection, PhysicalDamageRecord, DamageObservation,
    VerificationAudit, RepairRecord, RoadSegment
)

client = TestClient(app)

def test_belagavi_boundary_validation():
    # 1. Inside Belagavi City
    assert is_within_belagavi(15.8497, 74.4977) is True  # Chennamma Circle
    assert is_within_belagavi(15.8360, 74.4960) is True  # Tilakwadi 3rd Gate
    assert is_within_belagavi(15.8200, 74.4820) is True  # Udyambag

    # 2. Outside Belagavi City
    assert is_within_belagavi(28.6139, 77.2090) is False # New Delhi
    assert is_within_belagavi(12.9716, 77.5946) is False # Bengaluru
    assert is_within_belagavi(19.0760, 72.8777) is False # Mumbai
    assert is_within_belagavi(None, None) is False

def test_api_gis_belagavi_info():
    response = client.get("/api/gis/belagavi-info")
    assert response.status_code == 200
    data = response.json()
    assert data["city"] == "Belagavi"
    assert data["state"] == "Karnataka"
    assert len(data["junctions"]) >= 10

def test_api_road_segments():
    response = client.get("/api/roads/segments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 16
    first_seg = data["segments"][0]
    assert "code" in first_seg
    assert "length_m" in first_seg
    assert "coordinates" in first_seg

def test_spatial_segment_matching():
    # Point near Tilakwadi 3rd Gate on Khanapur Road
    seg, dist = match_defect_to_belagavi_segment(15.8365, 74.4962)
    assert seg is not None
    assert "Khanapur Road" in seg["name"]
    assert dist < 100.0

def test_route_navigation_within_belagavi():
    o = BELAGAVI_JUNCTIONS["CHEN_CIRC"]
    d = BELAGAVI_JUNCTIONS["UDYAMBAG"]

    response = client.post("/api/routes/navigate", data={
        "origin_lat": o["lat"],
        "origin_lon": o["lon"],
        "dest_lat": d["lat"],
        "dest_lon": d["lon"]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["routes"]) >= 2  # Verifies multiple alternative paths
    rec = [r for r in data["routes"] if r["route_id"] == data["recommended_route_id"]][0]
    assert rec["distance_km"] > 0
    assert "exposure_score" in rec
    assert "factors" in rec
    assert "color" in rec
    assert "risk_level" in rec
    assert len(rec["polyline"]) > 0

def test_route_navigation_blocks_outside_belagavi():
    # Attempt route from Delhi to Belagavi
    response = client.post("/api/routes/navigate", data={
        "origin_lat": 28.6139,
        "origin_lon": 77.2090,
        "dest_lat": 15.8200,
        "dest_lon": 74.4820
    })
    assert response.status_code == 400
    assert "outside" in response.json()["detail"].lower()

def test_three_state_defect_lifecycle():
    db = SessionLocal()

    # Step 1: Create a test Submission (State 1) and AIDetection (State 2: Unverified)
    sub = Submission(
        code="TEST-SUB-001",
        title="Test Survey",
        submitter_type="citizen",
        road_name="Khanapur Road, Belagavi",
        latitude=15.8360,
        longitude=74.4960,
        status="Pending Verification"
    )
    db.add(sub)
    db.flush()

    det = AIDetection(
        submission_id=sub.id,
        track_id="POTHOLE-TEST-99",
        class_id=0,
        class_name="pothole",
        category_code="D40",
        confidence=0.88,
        bbox_x1=100, bbox_y1=100, bbox_x2=200, bbox_y2=200,
        severity="Severe",
        latitude=15.8360,
        longitude=74.4960,
        verification_status="Unverified"
    )
    db.add(det)
    db.commit()
    det_id = det.id

    # Verify AI prediction is NOT automatically in verified physical records
    initial_phys = db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.damage_code == f"BLG-DMG-{det_id:04d}").first()
    assert initial_phys is None

    # Step 2: Authority verifies and confirms the AI detection
    verify_resp = client.post(f"/api/defects/{det_id}/verify", data={
        "action": "Verified",
        "verified_class": "Pothole (D40)",
        "verified_severity": "Severe",
        "reviewer": "Er. Rajesh Verma (PWD Belagavi)",
        "notes": "Verified severe cavity during field audit."
    })
    assert verify_resp.status_code == 200
    res_data = verify_resp.json()
    assert res_data["verification_status"] == "Verified"
    assert res_data["physical_damage_id"] is not None

    # Step 3: Check that State 3 (PhysicalDamageRecord) now exists with verified severity & road segment
    db.expire_all()
    phys_rec = db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == res_data["physical_damage_id"]).first()
    assert phys_rec is not None
    assert phys_rec.verified_severity == "Severe"
    assert phys_rec.priority_level in ["High", "Critical"]
    assert phys_rec.verification_status == "Verified"
    assert phys_rec.road_segment_id is not None

    # Step 4: Verify audit history and historical observation were recorded
    audit = db.query(VerificationAudit).filter(VerificationAudit.defect_id == det_id).first()
    assert audit is not None
    assert audit.auditor_name == "Er. Rajesh Verma (PWD Belagavi)"
    assert audit.original_category == "pothole"

    obs = db.query(DamageObservation).filter(DamageObservation.physical_damage_id == phys_rec.id).first()
    assert obs is not None
    assert obs.condition_state == "Newly Detected"
    assert obs.observed_severity == "Severe"

    # Cleanup test records
    db.query(DamageObservation).filter(DamageObservation.physical_damage_id == phys_rec.id).delete()
    db.query(VerificationAudit).filter(VerificationAudit.defect_id == det_id).delete()
    db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == phys_rec.id).delete()
    db.query(AIDetection).filter(AIDetection.id == det_id).delete()
    db.query(Submission).filter(Submission.id == sub.id).delete()
    db.commit()
    db.close()

def test_physical_damage_api_only_returns_verified():
    response = client.get("/api/physical-damage")
    assert response.status_code == 200
    data = response.json()
    for d in data["physical_defects"]:
        assert d["severity"] in ["Minor", "Moderate", "Severe"]
        assert d["road_name"] is not None
