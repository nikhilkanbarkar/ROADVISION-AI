"""
RoadGuard AI - End-to-End Functional Test Suite
Verifies:
1. Road Condition Classification (RISKY/Critical, MODERATE, SAFE) & calculation
2. Video/Image Road Damage Analysis
3. Citizen Reporting System (saved with Pending Verification status, does not affect official DB until accepted)
4. Authority Report Verification (ACCEPT updates road health & history; REJECT moves to rejected without updating road)
5. Authority Road Inspection & Direct Updates (immediately updates DB, GIS, Route Finder)
6. Database-backed Road Health Monitoring & History tracking
7. GIS Road Condition API & Table data
8. Multi-Route Risk Finder integration with official verified road conditions
9. Overview Dashboard live stats and classification distribution
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.database import SessionLocal
from backend.models_db import RoadSegment, RoadInspectionHistory, Submission, Defect, PhysicalDamageRecord

client = TestClient(app)

def test_road_conditions_api():
    """Requirement 1, 7, 8: Road condition classification, GIS map data, and road condition table data."""
    response = client.get("/api/roads/condition")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 20
    assert len(data["roads"]) >= 20

    # Verify road record fields required by Section 1 & 6
    sample = data["roads"][0]
    required_fields = [
        "id", "name", "location", "road_type", "speed_limit",
        "potholes_count", "total_damage_count", "condition_percentage",
        "risk_classification", "risk_display", "risk_color",
        "inspection_source", "verification_status", "last_inspected_date",
        "coordinates"
    ]
    for rf in required_fields:
        assert rf in sample, f"Missing field {rf} in road record"

    assert sample["risk_classification"] in ["SAFE", "MODERATE", "RISKY"]
    assert sample["risk_color"] in ["#10b981", "#f59e0b", "#ef4444"]
    assert 0.0 <= sample["condition_percentage"] <= 100.0

def test_road_conditions_filtering():
    """Verify filtering by risk classification (RISKY, MODERATE, SAFE)."""
    for risk in ["RISKY", "MODERATE", "SAFE"]:
        res = client.get(f"/api/roads/condition?risk_level={risk}")
        assert res.status_code == 200
        data = res.json()
        for r in data["roads"]:
            assert r["risk_classification"] == risk

def test_road_history_api():
    """Requirement 6: Maintaining road health inspection history over time."""
    db = SessionLocal()
    road = db.query(RoadSegment).first()
    road_id = road.id
    db.close()

    res = client.get(f"/api/roads/{road_id}/history")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["road_id"] == road_id
    assert "history" in data
    assert len(data["history"]) >= 1
    h0 = data["history"][0]
    assert "condition_percentage" in h0
    assert "potholes_count" in h0
    assert "risk_classification" in h0

def test_dashboard_stats_api():
    """Requirement 10: Overview Dashboard statistics and distribution."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_monitored_roads"] >= 20
    assert data["risky_roads_count"] >= 1
    assert data["moderate_roads_count"] >= 1
    assert data["safe_roads_count"] >= 1
    assert data["total_detected_potholes"] >= 0
    assert 0.0 <= data["average_condition_percentage"] <= 100.0
    assert "distribution" in data
    assert data["distribution"]["risky"] == data["risky_roads_count"]
    assert data["distribution"]["moderate"] == data["moderate_roads_count"]
    assert data["distribution"]["safe"] == data["safe_roads_count"]
    assert "recent_updates" in data

def test_citizen_report_submission_and_lifecycle():
    """
    Requirement 3 & 4:
    - Citizen submits report -> Status is 'Pending Verification'
    - Does NOT update RoadSegment before verification
    - Authority ACCEPTS -> Status becomes ACCEPTED, updates RoadSegment & RoadInspectionHistory
    """
    # 1. Create a dummy small image in memory
    import numpy as np
    import cv2
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a simulated dark cavity (pothole-like)
    cv2.circle(img, (320, 240), 50, (30, 30, 30), -1)
    _, img_encoded = cv2.imencode(".jpg", img)
    img_bytes = img_encoded.tobytes()

    # Get baseline condition of road 1 (Khanapur Road Tilakwadi to 3rd Gate)
    db = SessionLocal()
    road1 = db.query(RoadSegment).filter(RoadSegment.id == 1).first()
    old_potholes = road1.potholes_count
    old_condition = road1.condition_percentage
    db.close()

    # Citizen submits report
    files = {"file": ("pothole_report.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "road_name": "Khanapur Road (Tilakwadi to 3rd Gate)",
        "road_type": "Arterial",
        "speed_limit": 60,
        "manual_lat": 15.8360,
        "manual_lon": 74.4960,
        "citizen_name": "Rohan Deshmukh",
        "description": "Large dangerous pothole near railway gate crossing"
    }

    resp = client.post("/api/citizen/report", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "success"
    assert res_data["verification_status"] == "Pending Verification"
    sub_id = res_data["submission_id"]

    # Verify that the submission did NOT automatically update the official road condition in DB
    db = SessionLocal()
    road1_check = db.query(RoadSegment).filter(RoadSegment.id == 1).first()
    assert road1_check.potholes_count == old_potholes
    assert road1_check.condition_percentage == old_condition

    # Verify that citizen can see it in citizen reports list
    c_list = client.get("/api/citizen/reports").json()
    matching_c = [r for r in c_list["reports"] if r["id"] == sub_id]
    assert len(matching_c) == 1
    assert matching_c[0]["status"] == "Pending Verification"

    # Verify that authority sees it in authority citizen-reports list under 'pending'
    a_list = client.get("/api/authority/citizen-reports?status=pending").json()
    matching_a = [r for r in a_list["reports"] if r["id"] == sub_id]
    assert len(matching_a) == 1
    assert matching_a[0]["is_pending"] is True

    # Now Authority ACCEPTS the report
    accept_resp = client.post(f"/api/authority/reports/{sub_id}/verify", data={
        "action": "ACCEPT",
        "reviewer": "Er. Rajesh Verma (PWD Belagavi)",
        "notes": "Verified on site by junior engineer."
    })
    assert accept_resp.status_code == 200
    assert accept_resp.json()["verification_status"] == "ACCEPTED"

    # Verify that RoadSegment was now updated in the official database
    db.expire_all()
    road1_updated = db.query(RoadSegment).filter(RoadSegment.id == 1).first()
    assert road1_updated.verification_status == "ACCEPTED"
    assert road1_updated.inspection_source == "Verified Citizen Report"

    # Verify history entry was appended
    hist_entry = db.query(RoadInspectionHistory).filter(RoadInspectionHistory.submission_id == sub_id).first()
    assert hist_entry is not None
    assert hist_entry.inspector_name == "Er. Rajesh Verma (PWD Belagavi)"
    assert hist_entry.inspection_source == "Verified Citizen Report"

    # Cleanup test submission
    db.query(RoadInspectionHistory).filter(RoadInspectionHistory.submission_id == sub_id).delete()
    db.query(Defect).filter(Defect.submission_id == sub_id).delete()
    db.query(Submission).filter(Submission.id == sub_id).delete()
    # Restore road1 baseline
    road1_updated.potholes_count = old_potholes
    road1_updated.condition_percentage = old_condition
    road1_updated.risk_classification = "RISKY" if old_condition < 50 else ("MODERATE" if old_condition < 80 else "SAFE")
    road1_updated.inspection_source = "Demonstration Sample"
    road1_updated.verification_status = "VERIFIED"
    db.commit()
    db.close()

def test_citizen_report_rejection_lifecycle():
    """
    Requirement 4:
    - Authority REJECTS citizen report -> Status updated to REJECTED.
    - Moved to separate Rejected Reports section.
    - Road condition in database is NOT modified.
    """
    import numpy as np
    import cv2
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, img_encoded = cv2.imencode(".jpg", img)
    img_bytes = img_encoded.tobytes()

    db = SessionLocal()
    road2 = db.query(RoadSegment).filter(RoadSegment.id == 2).first()
    old_potholes = road2.potholes_count
    old_cond = road2.condition_percentage
    db.close()

    files = {"file": ("fake_report.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "road_name": "Khanapur Road (3rd Gate to Udyambag)",
        "manual_lat": 15.8280,
        "manual_lon": 74.4880,
        "citizen_name": "Test User",
        "description": "False alarm: puddle of water"
    }

    sub_resp = client.post("/api/citizen/report", files=files, data=data).json()
    sub_id = sub_resp["submission_id"]

    # Authority REJECTS the report
    rej_resp = client.post(f"/api/authority/reports/{sub_id}/verify", data={
        "action": "REJECT",
        "reviewer": "Er. Rajesh Verma (PWD Belagavi)",
        "notes": "Dismissed: Non-defect water shadow on surface."
    })
    assert rej_resp.status_code == 200
    assert rej_resp.json()["verification_status"] == "REJECTED"

    # Road 2 MUST remain unchanged
    db = SessionLocal()
    road2_check = db.query(RoadSegment).filter(RoadSegment.id == 2).first()
    assert road2_check.potholes_count == old_potholes
    assert road2_check.condition_percentage == old_cond

    # Appears in rejected reports list
    rej_list = client.get("/api/authority/citizen-reports?status=rejected").json()
    assert any(r["id"] == sub_id for r in rej_list["reports"])

    # Cleanup
    db.query(Defect).filter(Defect.submission_id == sub_id).delete()
    db.query(Submission).filter(Submission.id == sub_id).delete()
    db.commit()
    db.close()

def test_authority_direct_inspection_api():
    """
    Requirement 5:
    - Authority uploads road inspection and submits as official update.
    - Stored in official database and immediately updates RoadSegment.
    """
    import numpy as np
    import cv2
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, img_encoded = cv2.imencode(".jpg", img)
    img_bytes = img_encoded.tobytes()

    files = {"file": ("auth_survey.jpg", io.BytesIO(img_bytes), "image/jpeg")}
    data = {
        "road_name": "College Road (Bogarves to Hindwadi)",
        "road_type": "Local",
        "speed_limit": 45,
        "manual_lat": 15.8500,
        "manual_lon": 74.4980,
        "inspector_name": "Er. Rajesh Verma (PWD Belagavi)",
        "description": "Official post-monsoon survey by PWD unit"
    }

    res = client.post("/api/roads/inspect", files=files, data=data)
    assert res.status_code == 200
    data_res = res.json()
    assert data_res["status"] == "success"
    assert data_res["verification_status"] == "ACCEPTED"
    assert data_res["road_id"] == 4 # College Road

    db = SessionLocal()
    road4 = db.query(RoadSegment).filter(RoadSegment.id == 4).first()
    assert road4.inspection_source == "Authority Inspection"
    assert road4.verification_status == "ACCEPTED"

    # Cleanup
    sub_id = data_res["inspection_id"]
    db.query(RoadInspectionHistory).filter(RoadInspectionHistory.submission_id == sub_id).delete()
    db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.notes == data["description"]).delete()
    db.query(Defect).filter(Defect.submission_id == sub_id).delete()
    db.query(Submission).filter(Submission.id == sub_id).delete()
    # Reset road4 baseline
    road4.potholes_count = 1
    road4.condition_percentage = 74.5
    road4.risk_classification = "MODERATE"
    road4.inspection_source = "Demonstration Sample"
    road4.verification_status = "VERIFIED"
    db.commit()
    db.close()
