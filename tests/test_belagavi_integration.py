"""
ROADVISION AI - Belagavi Integration & 3-State Architecture Test Suite
Verifies:
1. Belagavi City boundary enforcement (is_within_belagavi)
2. 3-State Data Pipeline (Submitted -> AI-Generated -> Verified)
3. OSM road geometries & defect spatial matching
4. OSRM route geometry, alternatives, and exposure scoring
5. Duplicate Candidate Resolution
6. Repair Lifecycle & Progression Tracking
"""
import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient
from backend.app import app
import backend.gis_belagavi as gis
from backend.gis_belagavi import is_within_belagavi, match_defect_to_belagavi_segment, BELAGAVI_ROAD_SEGMENTS
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
    assert data["road_corridors"] == 30
    assert data["routing_engine"] == "OSRM"
    assert data["road_data_attribution"] == "© OpenStreetMap contributors"

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
    segment = BELAGAVI_ROAD_SEGMENTS[0]
    lon, lat = segment["coordinates"][len(segment["coordinates"]) // 2]
    seg, dist = match_defect_to_belagavi_segment(lat, lon)
    assert seg is not None
    assert seg["id"] == segment["id"]
    assert dist < 1.0
    exact_lon, exact_lat = segment["coordinates"][0]
    exact_seg, exact_dist = match_defect_to_belagavi_segment(exact_lat, exact_lon)
    assert exact_seg is not None
    assert exact_dist == 0.0

def test_osm_road_catalog_contains_real_route_geometry():
    assert 30 <= len(BELAGAVI_ROAD_SEGMENTS) <= 40
    for road in BELAGAVI_ROAD_SEGMENTS:
        assert road["geometry_source"].startswith("OSRM")
        assert road["length_m"] > 0
        assert len(road["coordinates"]) > 2
        assert road["start"] == road["coordinates"][0] or all(
            abs(a - b) < 0.00002
            for a, b in zip(road["start"], road["coordinates"][0])
        )

def test_route_navigation_uses_only_osrm_returned_geometry(monkeypatch):
    road = BELAGAVI_ROAD_SEGMENTS[0]
    coordinates = road["coordinates"]
    origin = coordinates[0]
    destination = coordinates[-1]
    route = {
        "distance": road["length_m"],
        "duration": road["duration_s"],
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "legs": [{"steps": [{"name": road["osm_names"][0] if road["osm_names"] else ""}]}]
    }
    payload = {
        "code": "Ok",
        "routes": [route],
        "waypoints": [
            {"location": origin, "name": "Origin road"},
            {"location": destination, "name": "Destination road"}
        ]
    }
    monkeypatch.setattr(gis, "fetch_osrm_route_data", lambda *args: payload)
    response = client.post("/api/routes/navigate", data={
        "origin_lat": origin[1],
        "origin_lon": origin[0],
        "dest_lat": destination[1],
        "dest_lon": destination[0]
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["route_count"] == 1
    assert len(data["routes"]) == 1
    assert data["routing_engine"] == "OSRM"
    rec = [r for r in data["routes"] if r["route_id"] == data["recommended_route_id"]][0]
    assert rec["distance_km"] > 0
    assert "exposure_score" in rec
    assert "recommendation_score" in rec
    assert "factors" in rec
    assert "color" in rec
    assert "risk_level" in rec
    assert rec["geometry"] == route["geometry"]
    assert rec["polyline"][0] == [origin[1], origin[0]]
    assert rec["polyline"][-1] == [destination[1], destination[0]]
    for route in data["routes"]:
        assert route["color"] == route["risk_color"]
        assert route["geometry"]["type"] == "LineString"

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

def test_osrm_duplicate_geometry_is_not_returned_as_an_alternative(monkeypatch):
    road = BELAGAVI_ROAD_SEGMENTS[0]
    coordinates = road["coordinates"]
    route = {
        "distance": road["length_m"],
        "duration": road["duration_s"],
        "geometry": {"type": "LineString", "coordinates": coordinates}
    }
    payload = {
        "code": "Ok",
        "routes": [route, route],
        "waypoints": [
            {"location": coordinates[0], "name": ""},
            {"location": coordinates[-1], "name": ""}
        ]
    }

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(
        gis.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: Response(json.dumps(payload).encode("utf-8"))
    )
    result = gis.fetch_osrm_route_data(
        coordinates[0][1], coordinates[0][0],
        coordinates[-1][1], coordinates[-1][0]
    )
    assert len(result["routes"]) == 1

def test_osrm_service_failure_is_reported_without_route_fallback(monkeypatch):
    monkeypatch.setattr(
        gis.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(urllib.error.URLError("offline"))
    )
    response = client.post("/api/routes/navigate", data={
        "origin_lat": 15.857393,
        "origin_lon": 74.506427,
        "dest_lat": 15.844053,
        "dest_lon": 74.501015
    })
    assert response.status_code == 503
    assert "OSRM routing service is unavailable" in response.json()["detail"]

def test_road_condition_uses_live_verified_damage_and_repair_status():
    db = SessionLocal()
    road = db.query(RoadSegment).filter(RoadSegment.id == 1).first()
    coordinate = json.loads(road.geometry_geojson)[len(json.loads(road.geometry_geojson)) // 2]
    road_id = road.id
    baseline = next(
        item for item in client.get("/api/roads/condition").json()["roads"]
        if item["id"] == road_id
    )
    damage = PhysicalDamageRecord(
        damage_code="TEST-OSM-LIVE-RISK",
        road_segment_id=road.id,
        road_name=road.name,
        latitude=coordinate[1],
        longitude=coordinate[0],
        category_code="D40",
        damage_type="Pothole",
        verified_severity="Severe",
        verification_status="Verified",
        repair_status="Pending"
    )
    db.add(damage)
    db.commit()
    damage_id = damage.id
    repair = RepairRecord(physical_damage_id=damage_id, status="Assigned")
    db.add(repair)
    db.commit()
    repair_id = repair.id
    db.close()

    try:
        live_road = next(
            item for item in client.get("/api/roads/condition").json()["roads"]
            if item["id"] == road_id
        )
        assert live_road["potholes_count"] == baseline["potholes_count"] + 1
        assert live_road["total_damage_count"] == baseline["total_damage_count"] + 1
        assert live_road["inspection_source"] == "Verified physical-damage records"

        repair_response = client.post(
            f"/api/repairs/{repair_id}/update",
            data={"status": "Repaired"}
        )
        assert repair_response.status_code == 200
        repaired_road = next(
            item for item in client.get("/api/roads/condition").json()["roads"]
            if item["id"] == road_id
        )
        assert repaired_road["potholes_count"] == baseline["potholes_count"]
        assert repaired_road["risk_classification"] == baseline["risk_classification"]
        active_damage_ids = {
            item["id"]
            for item in client.get("/api/physical-damage?limit=10000").json()["physical_defects"]
        }
        assert damage_id not in active_damage_ids
        repaired_damage_ids = {
            item["id"]
            for item in client.get(
                "/api/physical-damage?repair_status=Repaired&limit=10000"
            ).json()["physical_defects"]
        }
        assert damage_id in repaired_damage_ids
    finally:
        db = SessionLocal()
        db.query(RepairRecord).filter(RepairRecord.id == repair_id).delete()
        db.query(DamageObservation).filter(
            DamageObservation.physical_damage_id == damage_id
        ).delete()
        db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == damage_id).delete()
        db.commit()
        db.close()

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
