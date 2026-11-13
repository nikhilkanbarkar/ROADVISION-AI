"""
ROADVISION AI - Comprehensive Test Suite for Duplicate Report Detection
Tests all 10 Mandatory Scenarios specified in the project specification:
- Scenario 1: Same Pothole, Different Citizens
- Scenario 2: Same Pothole, Different Angles / Lighting (Neural Embedding Similarity)
- Scenario 3: Distinct Nearby Potholes (Separation based on Category/Visuals)
- Scenario 4: Video Frame Consolidation (ByteTrack frame-level deduplication)
- Scenario 5: Citizen Report Followed by Authority Inspection
- Scenario 6: Ambiguous Match Flagged for Verification
- Scenario 7: Brand New Pothole Creation
- Scenario 8: Historical Progression of Pothole Over Time
- Scenario 9: Data Integrity & Cascade / Orphan Prevention
- Scenario 10: Downstream Impact on GIS Map & Route Navigation
"""
import io
import os
import json
import cv2
import numpy as np
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import SessionLocal
from backend.models_db import (
    RoadSegment, Submission, Defect, PhysicalDamageRecord,
    DamageObservation, DuplicateMatch
)
from backend.duplicate_engine import (
    haversine_distance_meters,
    hamming_similarity,
    cosine_similarity,
    extract_image_embedding,
    evaluate_duplicate_multi_signal,
    evaluate_duplicate_candidate,
    find_best_physical_damage_match,
    DUPLICATE_GPS_RADIUS_METERS
)
from backend.tracker import VideoDamageTracker

client = TestClient(app)

def create_synthetic_pothole_image(radius=40, angle_deg=0, brightness=128):
    """Generates synthetic road damage image for deterministic visual tests."""
    img = np.full((240, 320, 3), brightness, dtype=np.uint8)
    # Dark asphalt texture
    cv2.circle(img, (160, 120), radius, (30, 30, 30), -1)
    cv2.ellipse(img, (160, 120), (radius + 5, radius - 10), angle_deg, 0, 360, (15, 15, 15), -1)
    is_success, buffer = cv2.imencode(".jpg", img)
    return buffer.tobytes(), img


# ==============================================================================
# SCENARIO 1: SAME POTHOLE, DIFFERENT CITIZENS
# ==============================================================================
def test_scenario_1_same_pothole_different_citizens():
    """
    Two citizens report the same pothole from similar coordinates with similar photos.
    The second report must be classified as a CONFIRMED DUPLICATE or associate with the existing physical record.
    """
    img_bytes, _ = create_synthetic_pothole_image(radius=45)
    lat, lon = 15.8450, 74.5050 # Tilakwadi, Belagavi

    db_init = SessionLocal()
    db_init.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude.between(lat - 0.0002, lat + 0.0002),
        PhysicalDamageRecord.longitude.between(lon - 0.0002, lon + 0.0002)
    ).delete()
    db_init.commit()
    db_init.close()

    # Citizen 1 submits report
    res1 = client.post(
        "/api/citizen/report",
        files={"file": ("citizen1.jpg", img_bytes, "image/jpeg")},
        data={
            "road_name": "Khanapur Road, Belagavi",
            "citizen_name": "Aarav Patil",
            "manual_lat": lat,
            "manual_lon": lon
        }
    )
    assert res1.status_code == 200
    sub1_id = res1.json()["submission_id"]

    # Authority verifies Citizen 1's report -> creates PhysicalDamageRecord
    v_res = client.post(
        f"/api/authority/reports/{sub1_id}/verify",
        data={"action": "ACCEPTED", "reviewer": "Er. Rajesh Verma (PWD Belagavi)"}
    )
    assert v_res.status_code == 200

    db = SessionLocal()
    sub1 = db.query(Submission).filter(Submission.id == sub1_id).first()
    pdr1 = db.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude == lat,
        PhysicalDamageRecord.longitude == lon
    ).first()
    assert pdr1 is not None, "Physical damage record must exist after authority verification"
    initial_observed = pdr1.times_observed
    db.close()

    # Citizen 2 submits same pothole ~4 meters away with similar photo
    lat2, lon2 = 15.84503, 74.50502 # ~4m away
    res2 = client.post(
        "/api/citizen/report",
        files={"file": ("citizen2.jpg", img_bytes, "image/jpeg")},
        data={
            "road_name": "Khanapur Road, Belagavi",
            "citizen_name": "Deepa Kulkarni",
            "manual_lat": lat2,
            "manual_lon": lon2
        }
    )
    assert res2.status_code == 200
    sub2_id = res2.json()["submission_id"]

    db = SessionLocal()
    sub2 = db.query(Submission).filter(Submission.id == sub2_id).first()
    assert sub2.duplicate_status == "Confirmed_Duplicate", f"Expected Confirmed_Duplicate, got {sub2.duplicate_status}"
    assert sub2.physical_damage_id == pdr1.id, "Citizen 2 submission must link to existing PhysicalDamageRecord"

    # Authority accepts Citizen 2's report -> increments observation count, DOES NOT create duplicate physical record
    v_res2 = client.post(
        f"/api/authority/reports/{sub2_id}/verify",
        data={"action": "ACCEPTED", "reviewer": "Er. Rajesh Verma (PWD Belagavi)"}
    )
    assert v_res2.status_code == 200

    # Query fresh physical record from DB after authority verification
    pdr1_fresh = db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == sub2.physical_damage_id).first()
    assert pdr1_fresh.times_observed == initial_observed + 1, "times_observed must increment upon duplicate report verification"

    # Ensure no duplicate physical record with same coordinates exists
    same_loc_count = db.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude.between(lat - 0.0002, lat + 0.0002),
        PhysicalDamageRecord.longitude.between(lon - 0.0002, lon + 0.0002)
    ).count()
    assert same_loc_count == 1, "Only one consolidated physical damage record must exist for this physical pothole"
    db.close()


# ==============================================================================
# SCENARIO 2: SAME POTHOLE, DIFFERENT ANGLES / LIGHTING (NEURAL EMBEDDING)
# ==============================================================================
def test_scenario_2_same_pothole_different_angles_lighting():
    """
    Photo taken from a different angle / lighting. Perceptual dHash drops, but deep neural
    embedding cosine similarity preserves visual match, leading to CONFIRMED_DUPLICATE or NEEDS_VERIFICATION.
    """
    _, img_base = create_synthetic_pothole_image(radius=40, angle_deg=0, brightness=120)
    _, img_rotated = create_synthetic_pothole_image(radius=40, angle_deg=35, brightness=160)

    # Extract deep neural embeddings
    emb1 = extract_image_embedding(img_base)
    emb2 = extract_image_embedding(img_rotated)

    assert emb1 is not None and len(emb1) > 0
    assert emb2 is not None and len(emb2) > 0

    cos_sim = cosine_similarity(emb1, emb2)
    assert cos_sim >= 0.65, f"Deep embedding cosine similarity across rotation/lighting should be high (got {cos_sim})"

    # Multi-signal evaluation for same location (7m apart)
    from types import SimpleNamespace
    cand = SimpleNamespace(
        latitude=15.8500, longitude=74.5000,
        category_code="D40", class_name="pothole",
        image_hash="a1b2c3d4e5f60000",
        image_embedding=emb1
    )
    existing = SimpleNamespace(
        latitude=15.85005, longitude=74.50004, # ~7 meters away
        category_code="D40", damage_type="Pothole",
        image_hash="ffffffff00000000", # Perceptual hash intentionally different
        image_embedding=emb2
    )

    eval_res = evaluate_duplicate_multi_signal(cand, existing, search_radius_m=25.0)
    assert eval_res["decision"] in ["CONFIRMED_DUPLICATE", "NEEDS_VERIFICATION"], (
        f"Different camera angle/lighting must be CONFIRMED or NEEDS_VERIFICATION, got {eval_res['decision']}"
    )
    assert eval_res["decision"] != "NEW_DAMAGE", "Must not mistakenly classify same pothole from another angle as new damage"


# ==============================================================================
# SCENARIO 3: DISTINCT NEARBY POTHOLES
# ==============================================================================
def test_scenario_3_distinct_nearby_potholes():
    """
    Two different defects nearby (e.g. a pothole vs a longitudinal crack, or two visually distinct defects).
    Despite proximity, category or visual separation must result in NEW_DAMAGE classification.
    """
    from types import SimpleNamespace
    # Defect 1: Pothole
    cand_pothole = SimpleNamespace(
        latitude=15.8600, longitude=74.5100,
        category_code="D40", class_name="pothole",
        image_hash="1111222233334444",
        image_embedding=None
    )
    # Defect 2: Longitudinal crack 12m away
    cand_crack = SimpleNamespace(
        latitude=15.8601, longitude=74.5100, # ~11m away
        category_code="D00", damage_type="Longitudinal Crack",
        image_hash="9999888877776666",
        image_embedding=None
    )

    eval_res = evaluate_duplicate_multi_signal(cand_pothole, cand_crack, search_radius_m=25.0)
    assert eval_res["decision"] == "NEW_DAMAGE", f"Pothole and Crack must be classified as NEW_DAMAGE, got {eval_res['decision']}"
    assert eval_res["category_match"] is False


# ==============================================================================
# SCENARIO 4: VIDEO FRAME CONSOLIDATION (BYTETRACK DEDUPLICATION)
# ==============================================================================
def test_scenario_4_video_frame_consolidation():
    """
    A video inspection detects the same pothole across 30 consecutive frames.
    VideoDamageTracker must consolidate these into 1 observation, not 30 damage records.
    """
    tracker = VideoDamageTracker(max_missed=15, iou_threshold=0.25)

    # Simulate a tracked pothole moving across 30 video frames
    for f in range(30):
        # Slightly shifting bounding box as vehicle moves forward
        bbox = [100 + f, 120 + (f // 2), 180 + f, 190 + (f // 2)]
        detections = [{
            "category_code": "D40",
            "class_name": "pothole",
            "display_name": "Pothole",
            "bbox": bbox,
            "confidence": 0.88,
            "relative_area": 0.04,
            "severity": "Moderate"
        }]
        tracker.update_frame(detections, frame_idx=f, time_sec=f * 0.033)

    tracks = tracker.finalize()
    assert len(tracks) == 1, f"Expected exactly 1 consolidated track, got {len(tracks)}"
    assert tracks[0].category_code == "D40"
    assert tracks[0].detection_count == 30
    assert tracks[0].track_id.startswith("POTHOLE-")


# ==============================================================================
# SCENARIO 5: CITIZEN REPORT FOLLOWED BY AUTHORITY INSPECTION
# ==============================================================================
def test_scenario_5_citizen_report_followed_by_authority_inspection():
    """
    A citizen reports a pothole. Later, authority inspects the same road segment and records the same pothole.
    The authority inspection must link to the existing physical damage record rather than creating a duplicate.
    """
    img_bytes, _ = create_synthetic_pothole_image(radius=40)
    lat, lon = 15.8700, 74.5200

    db_init = SessionLocal()
    db_init.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude.between(lat - 0.0002, lat + 0.0002),
        PhysicalDamageRecord.longitude.between(lon - 0.0002, lon + 0.0002)
    ).delete()
    db_init.commit()
    db_init.close()

    # 1. Citizen reports pothole
    c_res = client.post(
        "/api/citizen/report",
        files={"file": ("citizen_init.jpg", img_bytes, "image/jpeg")},
        data={
            "road_name": "Congress Road, Belagavi",
            "citizen_name": "Mahesh Desai",
            "manual_lat": lat,
            "manual_lon": lon
        }
    )
    assert c_res.status_code == 200
    c_sub_id = c_res.json()["submission_id"]

    # 2. Authority verifies citizen report -> Official physical record is established
    client.post(
        f"/api/authority/reports/{c_sub_id}/verify",
        data={"action": "ACCEPTED", "reviewer": "Er. Rajesh Verma (PWD Belagavi)"}
    )

    db = SessionLocal()
    initial_pdr = db.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude == lat,
        PhysicalDamageRecord.longitude == lon
    ).first()
    assert initial_pdr is not None
    init_obs_count = initial_pdr.times_observed
    pdr_id = initial_pdr.id
    db.close()

    # 3. Authority executes direct official inspection on the same segment
    auth_res = client.post(
        "/api/roads/inspect",
        files={"file": ("auth_survey.jpg", img_bytes, "image/jpeg")},
        data={
            "road_name": "Congress Road, Belagavi",
            "inspector_name": "Er. Rajesh Verma (PWD Belagavi)",
            "manual_lat": lat + 0.00003, # ~3m away
            "manual_lon": lon + 0.00002
        }
    )
    assert auth_res.status_code == 200

    db = SessionLocal()
    updated_pdr = db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == pdr_id).first()
    assert updated_pdr.times_observed == init_obs_count + 1, "Authority inspection must increment times_observed on existing physical asset"

    # Confirm damage observation was logged
    obs = db.query(DamageObservation).filter(
        DamageObservation.physical_damage_id == pdr_id,
        DamageObservation.observer_type == "authority"
    ).first()
    assert obs is not None, "A DamageObservation must be created linking authority survey to the physical defect"
    db.close()


# ==============================================================================
# SCENARIO 6: AMBIGUOUS MATCH FLAGGED FOR VERIFICATION
# ==============================================================================
def test_scenario_6_ambiguous_match_flagged_for_verification():
    """
    A submission with borderline matching evidence is classified as NEEDS VERIFICATION
    and routed to the authority dashboard for manual resolution.
    """
    from types import SimpleNamespace
    # Ambiguous candidate: 18m away with moderate visual similarity (50%)
    cand = SimpleNamespace(
        latitude=15.8550, longitude=74.5150,
        category_code="D40", class_name="pothole",
        image_hash="a1b2c3d4e5f60000",
        image_embedding=None
    )
    existing = SimpleNamespace(
        latitude=15.85514, longitude=74.5151, # ~18m away
        category_code="D40", damage_type="Pothole",
        image_hash="a1b2c3d4ffffffff", # Partial hash match ~50%
        image_embedding=None
    )

    eval_res = evaluate_duplicate_multi_signal(cand, existing, search_radius_m=25.0)
    assert eval_res["decision"] == "NEEDS_VERIFICATION", f"Expected NEEDS_VERIFICATION, got {eval_res['decision']}"
    assert eval_res["needs_verification"] is True

    # Test resolution API: Authority marks candidate as separate damage
    db = SessionLocal()
    match = DuplicateMatch(
        spatial_distance_m=18.0,
        visual_similarity_pct=50.0,
        category_match=True,
        decision_status="Needs_Verification",
        status="Pending"
    )
    db.add(match)
    db.commit()
    match_id = match.id
    db.close()

    res = client.post(
        f"/api/duplicates/{match_id}/resolve",
        data={"action": "MARK_SEPARATE", "reviewer": "Er. Rajesh Verma (PWD Belagavi)"}
    )
    assert res.status_code == 200
    assert res.json()["action"] == "MARK_SEPARATE"

    db = SessionLocal()
    resolved_match = db.query(DuplicateMatch).filter(DuplicateMatch.id == match_id).first()
    assert resolved_match.status == "Dismissed"
    assert resolved_match.decision_status == "Marked_Separate"
    db.close()


# ==============================================================================
# SCENARIO 7: BRAND NEW POTHOLE CREATION
# ==============================================================================
def test_scenario_7_brand_new_pothole_creation():
    """
    A report of a pothole in a previously undamaged location creates a new physical damage record with a unique ID.
    """
    img_bytes, _ = create_synthetic_pothole_image(radius=35)
    # New coordinate away from existing defects
    new_lat, new_lon = 15.8850, 74.5450 # Kanbargi Road

    db_init = SessionLocal()
    db_init.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude.between(new_lat - 0.0002, new_lat + 0.0002),
        PhysicalDamageRecord.longitude.between(new_lon - 0.0002, new_lon + 0.0002)
    ).delete()
    db_init.commit()
    db_init.close()

    res = client.post(
        "/api/roads/inspect",
        files={"file": ("brand_new_defect.jpg", img_bytes, "image/jpeg")},
        data={
            "road_name": "Kanbargi Road, Belagavi",
            "inspector_name": "Er. Rajesh Verma (PWD Belagavi)",
            "manual_lat": new_lat,
            "manual_lon": new_lon
        }
    )
    assert res.status_code == 200
    insp_id = res.json()["inspection_id"]

    db = SessionLocal()
    pdr = db.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.latitude == new_lat,
        PhysicalDamageRecord.longitude == new_lon
    ).first()

    assert pdr is not None, "Brand new pothole must create a PhysicalDamageRecord"
    assert pdr.damage_code.startswith("BLG-DMG-")
    assert pdr.times_observed == 1
    assert pdr.verification_status == "Verified"

    # Confirm initial damage observation was logged
    obs = db.query(DamageObservation).filter(DamageObservation.physical_damage_id == pdr.id).first()
    assert obs is not None
    assert obs.condition_state == "Newly Detected"
    db.close()


# ==============================================================================
# SCENARIO 8: HISTORICAL PROGRESSION OVER TIME
# ==============================================================================
def test_scenario_8_historical_progression_over_time():
    """
    Multiple submissions over time observe the same pothole deteriorating.
    Observations track the progression while maintaining a single physical damage ID.
    """
    db_init = SessionLocal()
    old = db_init.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.damage_code == "BLG-DMG-HIST-TEST").first()
    if old:
        db_init.delete(old)
        db_init.commit()
    db_init.close()

    db = SessionLocal()
    # Create an initial physical damage record
    pdr = PhysicalDamageRecord(
        damage_code="BLG-DMG-HIST-TEST",
        road_name="Khanapur Road, Belagavi",
        latitude=15.8420,
        longitude=74.5020,
        category_code="D40",
        damage_type="Pothole",
        verified_severity="Minor",
        times_observed=1,
        verification_status="Verified"
    )
    db.add(pdr)
    db.commit()
    pdr_id = pdr.id

    # Observation 1: Month 1 (Newly Detected, Minor)
    obs1 = DamageObservation(
        physical_damage_id=pdr_id,
        observation_date=datetime.utcnow() - timedelta(days=60),
        observed_severity="Minor",
        condition_state="Newly Detected",
        observer_type="citizen",
        notes="Small shallow pothole starting to form."
    )
    # Observation 2: Month 2 (Worsened, Moderate)
    obs2 = DamageObservation(
        physical_damage_id=pdr_id,
        observation_date=datetime.utcnow() - timedelta(days=30),
        observed_severity="Moderate",
        condition_state="Worsened",
        observer_type="citizen",
        notes="Pothole expanded following monsoon rains."
    )
    # Observation 3: Month 3 (Worsened, Severe)
    obs3 = DamageObservation(
        physical_damage_id=pdr_id,
        observation_date=datetime.utcnow(),
        observed_severity="Severe",
        condition_state="Worsened",
        observer_type="authority",
        notes="Deep severe pothole requiring emergency asphalt patching."
    )
    db.add_all([obs1, obs2, obs3])
    pdr.times_observed = 3
    pdr.verified_severity = "Severe"
    db.commit()
    db.close()

    # Query history endpoint
    res = client.get(f"/api/physical-damage/{pdr_id}/history")
    assert res.status_code == 200
    data = res.json()
    assert data["damage_code"] == "BLG-DMG-HIST-TEST"
    assert data["total_observations"] == 3
    assert len(data["observations"]) == 3
    assert data["observations"][0]["condition_state"] == "Newly Detected"
    assert data["observations"][2]["observed_severity"] == "Severe"


# ==============================================================================
# SCENARIO 9: DATA INTEGRITY & CASCADE / ORPHAN PREVENTION
# ==============================================================================
def test_scenario_9_data_integrity_cascade_orphan_prevention():
    """
    Deleting a submission must not delete the consolidated physical damage record if other submissions reference it.
    Deleting a physical damage record must handle associated submissions gracefully.
    """
    db = SessionLocal()
    # 1. Create a physical damage record
    pdr = PhysicalDamageRecord(
        damage_code="BLG-DMG-ORPHAN-TEST",
        road_name="Civil Hospital Road, Belagavi",
        latitude=15.8650,
        longitude=74.5080,
        category_code="D40",
        verification_status="Verified",
        times_observed=2
    )
    db.add(pdr)
    db.commit()
    pdr_id = pdr.id

    # 2. Create two submissions referencing this physical record
    subA = Submission(code="CIT-TEST-A", title="Report A", file_path="dummy_a.jpg", physical_damage_id=pdr_id)
    subB = Submission(code="CIT-TEST-B", title="Report B", file_path="dummy_b.jpg", physical_damage_id=pdr_id)
    db.add_all([subA, subB])
    db.commit()
    subA_id = subA.id
    subB_id = subB.id

    # 3. Delete Submission A
    db.delete(subA)
    db.commit()

    # Verify physical damage record still exists and Submission B is intact
    remaining_pdr = db.query(PhysicalDamageRecord).filter(PhysicalDamageRecord.id == pdr_id).first()
    assert remaining_pdr is not None, "PhysicalDamageRecord must not be deleted when a single submission is removed"

    remaining_subB = db.query(Submission).filter(Submission.id == subB_id).first()
    assert remaining_subB is not None
    assert remaining_subB.physical_damage_id == pdr_id

    # Cleanup
    db.delete(remaining_subB)
    db.delete(remaining_pdr)
    db.commit()
    db.close()


# ==============================================================================
# SCENARIO 10: DOWNSTREAM IMPACT ON GIS MAP & ROUTE NAVIGATION
# ==============================================================================
def test_scenario_10_downstream_impact_on_gis_map_and_route_navigation():
    """
    Verify that the GIS map (/api/physical-damage) and route navigation (/api/routes/navigate)
    reflect consolidated physical damage records rather than raw report counts,
    preventing risk score inflation from duplicate submissions.
    """
    # Query physical damage endpoint (which powers the GIS map)
    res = client.get("/api/physical-damage")
    assert res.status_code == 200
    data = res.json()
    assert "physical_defects" in data
    defects = data["physical_defects"]

    # Verify every returned defect is a unique physical record (unique ID and damage code)
    ids = [d["id"] for d in defects]
    codes = [d["damage_code"] for d in defects]
    assert len(ids) == len(set(ids)), "GIS map physical damage records must have unique IDs (no duplicates)"
    assert len(codes) == len(set(codes)), "GIS map physical damage records must have unique damage codes"

    # Verify route navigation within Belagavi
    # Origin: Tilakwadi (15.8450, 74.5050), Destination: Civil Hospital (15.8620, 74.5080)
    nav_res = client.post(
        "/api/routes/navigate",
        data={
            "origin_lat": 15.8450,
            "origin_lon": 74.5050,
            "dest_lat": 15.8620,
            "dest_lon": 74.5080
        }
    )
    assert nav_res.status_code == 200
    nav_data = nav_res.json()
    assert "routes" in nav_data
    assert len(nav_data["routes"]) >= 1

    # Verify route safety scoring reflects verified consolidated damage
    for route in nav_data["routes"]:
        assert "exposure_score" in route
        assert "risk_level" in route
        assert 0.0 <= route["exposure_score"] <= 100.0
