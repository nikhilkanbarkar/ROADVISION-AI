"""
ROADVISION AI - Belagavi City Data Seeder
Populates the central geographical database with Belagavi road network segments,
realistic citizen and authority submissions, AI detections, verified physical damage records,
historical progression observations, and repair work orders.
"""
import os
import sys
import json
from datetime import datetime, timedelta

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.database import engine, SessionLocal, Base
from backend.models_db import (
    User, RoadSegment, Submission, AIDetection, PhysicalDamageRecord,
    DamageObservation, DuplicateMatch, VerificationAudit, RepairRecord,
    HistoricalComparison
)
from backend.gis_belagavi import (
    BELAGAVI_ROAD_SEGMENTS, is_within_belagavi, match_defect_to_belagavi_segment
)
from backend.config import UPLOADS_DIR, OUTPUTS_DIR

def seed_belagavi_database():
    print("[Belagavi Seeder] Dropping old tables and recreating clean schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Clear previous seed data
    db.query(VerificationAudit).delete()
    db.query(HistoricalComparison).delete()
    db.query(RepairRecord).delete()
    db.query(DuplicateMatch).delete()
    db.query(DamageObservation).delete()
    db.query(PhysicalDamageRecord).delete()
    db.query(AIDetection).delete()
    db.query(Submission).delete()
    db.query(RoadSegment).delete()
    db.commit()

    print("[Belagavi Seeder] Inserting Belagavi road network segments...")
    segment_map = {}
    for r in BELAGAVI_ROAD_SEGMENTS:
        seg = RoadSegment(
            id=r["id"],
            segment_code=r["code"],
            name=r["name"],
            road_type=r["road_type"],
            speed_limit=r["speed_limit"],
            from_node=r["from_node"],
            to_node=r["to_node"],
            start_lat=r["coordinates"][0][1],
            start_lon=r["coordinates"][0][0],
            end_lat=r["coordinates"][-1][1],
            end_lon=r["coordinates"][-1][0],
            length_m=r["length_m"],
            geometry_geojson=json.dumps(r["coordinates"]),
            surface_type=r["surface"]
        )
        db.add(seg)
        segment_map[r["code"]] = r["id"]
    db.commit()
    print(f"  Inserted {len(BELAGAVI_ROAD_SEGMENTS)} Belagavi road network segments.")

    # Users
    u_citizen = User(
        username="priya_belagavi",
        email="citizen@roadvision.in",
        name="Priya Sharma",
        role="citizen",
        department="Belagavi Motorist Association"
    )
    u_authority = User(
        username="er_verma_pwd",
        email="authority@pwd.gov.in",
        name="Er. Rajesh Verma",
        role="authority",
        department="Belagavi City Corporation (PWD Roads Division)"
    )
    db.add_all([u_citizen, u_authority])
    db.commit()

    print("[Belagavi Seeder] Seeding authentic Belagavi road damage records...")

    # ==========================================================================
    # SUBMISSION 1: Citizen Report on Khanapur Road (Tilakwadi)
    # Pothole + Alligator Cracks
    # ==========================================================================
    sub1 = Submission(
        code="CIT-BLG-202611-001",
        title="Citizen Report: Severe Pothole near Tilakwadi 3rd Railway Gate",
        submitter_type="citizen",
        submitter_name="Priya Sharma",
        user_id=u_citizen.id,
        media_type="image",
        file_path="data/uploads/nh48_survey_jan.jpg",
        annotated_path="data/outputs/annotated_nh48_survey_jan.jpg",
        thumbnail_path="data/outputs/annotated_nh48_survey_jan.jpg",
        upload_time=datetime.utcnow() - timedelta(days=22),
        road_name="Khanapur Road (near 3rd Railway Gate)",
        road_type="Arterial",
        speed_limit=60,
        weather_condition="Rainy/Wet",
        traffic_volume="High",
        description="Deep pothole causing vehicle swerving immediately after 3rd Railway Gate heading towards Udyambag.",
        latitude=15.8362,
        longitude=74.4965,
        location_name="Khanapur Road, Tilakwadi, Belagavi",
        within_belagavi=True,
        total_detections=2,
        unique_defects_count=2,
        minor_count=0,
        moderate_count=1,
        severe_count=1,
        risk_score=78.5,
        risk_level="Critical",
        status="Verified"
    )
    db.add(sub1)
    db.flush()

    # AI Detections for Submission 1 (State 2: AI-Generated)
    d1_1 = AIDetection(
        submission_id=sub1.id,
        track_id="POTHOLE-001",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.925,
        bbox_x1=180.0, bbox_y1=305.0, bbox_x2=340.0, bbox_y2=415.0,
        relative_area=0.043,
        severity="Severe",
        estimated_depth_tier="Deep",
        image_hash="7f7e7c381c1c1c1c",
        latitude=15.8362,
        longitude=74.4965,
        verification_status="Verified",
        verified_class="pothole",
        verified_severity="Severe",
        verified_by="Er. Rajesh Verma (Belagavi City Engineer)",
        verified_at=datetime.utcnow() - timedelta(days=21)
    )
    d1_2 = AIDetection(
        submission_id=sub1.id,
        track_id="CRACK-001",
        class_id=2,
        class_name="alligator_crack",
        category_code="D20",
        confidence=0.865,
        bbox_x1=415.0, bbox_y1=75.0, bbox_x2=475.0, bbox_y2=625.0,
        relative_area=0.035,
        severity="Moderate",
        estimated_depth_tier="Medium",
        image_hash="a1b2c3d4e5f60718",
        latitude=15.8362,
        longitude=74.4965,
        verification_status="Verified",
        verified_class="alligator_crack",
        verified_severity="Moderate",
        verified_by="Er. Rajesh Verma (Belagavi City Engineer)",
        verified_at=datetime.utcnow() - timedelta(days=21)
    )
    db.add_all([d1_1, d1_2])
    db.flush()

    # Physical Damage Record 1 (State 3: Verified Physical Defect in Belagavi)
    p_dmg1 = PhysicalDamageRecord(
        damage_code="BLG-DMG-001",
        road_segment_id=1, # Khanapur Road (Tilakwadi - 3rd Gate)
        road_name="Khanapur Road (3rd Railway Gate)",
        latitude=15.8362,
        longitude=74.4965,
        within_belagavi=True,
        category_code="D40",
        damage_type="Pothole",
        verified_severity="Severe",
        verified_depth_tier="Deep",
        verified_risk_score=78.5,
        priority_level="Critical",
        verification_status="Verified",
        verified_by="Er. Rajesh Verma",
        verified_at=datetime.utcnow() - timedelta(days=21),
        evidence_photo_path="data/outputs/annotated_nh48_survey_jan.jpg",
        image_hash="7f7e7c381c1c1c1c",
        first_reported_date=datetime.utcnow() - timedelta(days=22),
        latest_inspection_date=datetime.utcnow() - timedelta(days=21),
        times_observed=1,
        repair_status="Assigned",
        notes="High vehicular speed corridor. Pothole depth exceeds 6cm."
    )
    db.add(p_dmg1)
    db.flush()

    d1_1.physical_damage_id = p_dmg1.id

    # Observation 1
    obs1 = DamageObservation(
        physical_damage_id=p_dmg1.id,
        submission_id=sub1.id,
        observation_date=datetime.utcnow() - timedelta(days=22),
        observed_severity="Severe",
        observed_area_pct=0.043,
        condition_state="Newly Detected",
        evidence_photo_path="data/outputs/annotated_nh48_survey_jan.jpg",
        observer_type="citizen",
        notes="Initial citizen mobile report verified by municipal engineer."
    )
    db.add(obs1)

    # Verification Audit Record (Preserving original AI vs corrected)
    audit1 = VerificationAudit(
        submission_id=sub1.id,
        physical_damage_id=p_dmg1.id,
        original_category="D40 (pothole)",
        original_severity="Severe",
        original_bbox="[180, 305, 340, 415]",
        original_risk_score=78.5,
        corrected_category="D40 (pothole)",
        corrected_severity="Severe",
        corrected_bbox="[180, 305, 340, 415]",
        corrected_risk_score=78.5,
        action="Approved",
        auditor_name="Er. Rajesh Verma (Belagavi City Engineer)",
        comments="Confirmed severe cavity. Urgent cold-mix patch required."
    )
    db.add(audit1)

    # Repair Record for BLG-DMG-001
    rep1 = RepairRecord(
        physical_damage_id=p_dmg1.id,
        submission_id=sub1.id,
        defect_id=d1_1.id,
        status="Repair in Progress",
        priority="Emergency",
        assigned_authority="Belagavi City Corporation (PWD)",
        assigned_contractor="Karnataka Urban Infrastructure Maintenance Ltd",
        created_at=datetime.utcnow() - timedelta(days=20),
        scheduled_repair_date=datetime.utcnow() + timedelta(days=2),
        before_photo_path="data/outputs/annotated_nh48_survey_jan.jpg",
        remarks="Emergency patch order dispatched. Awaiting final bitumen layer."
    )
    db.add(rep1)

    # ==========================================================================
    # SUBMISSION 2: Duplicate Citizen Report on Same Khanapur Road Pothole (8m away)
    # ==========================================================================
    sub2 = Submission(
        code="CIT-BLG-202611-002",
        title="Citizen Mobile Grievance: Big pothole near 3rd gate",
        submitter_type="citizen",
        submitter_name="Sunil Patil",
        media_type="image",
        file_path="data/uploads/citizen_report_nh48.jpg",
        annotated_path="data/outputs/annotated_citizen_report_nh48.jpg",
        thumbnail_path="data/outputs/annotated_citizen_report_nh48.jpg",
        upload_time=datetime.utcnow() - timedelta(days=16),
        road_name="Khanapur Road (near 3rd Railway Gate)",
        road_type="Arterial",
        speed_limit=60,
        weather_condition="Clear/Dry",
        traffic_volume="High",
        description="Dangerous hole in road right in front of railway gate.",
        latitude=15.83625, # ~6.5m offset
        longitude=74.49654,
        location_name="Khanapur Road, Tilakwadi, Belagavi",
        within_belagavi=True,
        total_detections=1,
        unique_defects_count=1,
        minor_count=0,
        moderate_count=0,
        severe_count=1,
        risk_score=74.2,
        risk_level="High",
        status="Duplicate"
    )
    db.add(sub2)
    db.flush()

    d2_1 = AIDetection(
        submission_id=sub2.id,
        track_id="POTHOLE-002",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.892,
        bbox_x1=182.0, bbox_y1=308.0, bbox_x2=338.0, bbox_y2=412.0,
        relative_area=0.041,
        severity="Severe",
        estimated_depth_tier="Deep",
        image_hash="7f7e7c381c1c1c1c", # Identical visual hash
        latitude=15.83625,
        longitude=74.49654,
        verification_status="Verified"
    )
    db.add(d2_1)
    db.flush()

    # Link as duplicate match candidate
    dup_match = DuplicateMatch(
        new_defect_id=d2_1.id,
        existing_defect_id=d1_1.id,
        candidate_submission_id=sub2.id,
        physical_damage_id=p_dmg1.id,
        spatial_distance_m=6.8,
        visual_similarity_pct=98.5,
        category_match=True,
        status="Confirmed_Duplicate",
        resolution_notes="Duplicate citizen report for BLG-DMG-001 within 6.8m radius. Priority upvoted.",
        resolved_by="Er. Rajesh Verma",
        resolved_at=datetime.utcnow() - timedelta(days=15)
    )
    db.add(dup_match)

    # Observation 2 for BLG-DMG-001: Unchanged / Active
    obs2 = DamageObservation(
        physical_damage_id=p_dmg1.id,
        submission_id=sub2.id,
        observation_date=datetime.utcnow() - timedelta(days=16),
        observed_severity="Severe",
        observed_area_pct=0.041,
        condition_state="Unchanged",
        evidence_photo_path="data/outputs/annotated_citizen_report_nh48.jpg",
        observer_type="citizen",
        notes="Re-observed by second citizen. Pothole remains active."
    )
    db.add(obs2)
    p_dmg1.times_observed = 2

    # ==========================================================================
    # SUBMISSION 3: College Road (Bogarves to Hindwadi) - Moderate Distress
    # ==========================================================================
    sub3 = Submission(
        code="CIT-BLG-202611-003",
        title="Pavement Cracking on College Road near Bogarves",
        submitter_type="citizen",
        submitter_name="Amit Kulkarni",
        media_type="image",
        file_path="data/uploads/ring_road_oct.jpg",
        annotated_path="data/outputs/annotated_ring_road_oct.jpg",
        thumbnail_path="data/outputs/annotated_ring_road_oct.jpg",
        upload_time=datetime.utcnow() - timedelta(days=14),
        road_name="College Road (near Bogarves Circle)",
        road_type="Local",
        speed_limit=45,
        weather_condition="Clear/Dry",
        traffic_volume="Moderate",
        description="Longitudinal thermal fracture running along the left bicycle lane.",
        latitude=15.8525,
        longitude=74.4998,
        location_name="College Road, Belagavi",
        within_belagavi=True,
        total_detections=1,
        unique_defects_count=1,
        minor_count=1,
        moderate_count=0,
        severe_count=0,
        risk_score=28.0,
        risk_level="Moderate",
        status="Verified"
    )
    db.add(sub3)
    db.flush()

    d3_1 = AIDetection(
        submission_id=sub3.id,
        track_id="CRACK-002",
        class_id=0,
        class_name="longitudinal_crack",
        category_code="D00",
        confidence=0.812,
        bbox_x1=400.0, bbox_y1=100.0, bbox_x2=450.0, bbox_y2=500.0,
        relative_area=0.018,
        severity="Minor",
        estimated_depth_tier="Shallow",
        image_hash="b2c3d4e5f6071829",
        latitude=15.8525,
        longitude=74.4998,
        verification_status="Verified"
    )
    db.add(d3_1)
    db.flush()

    p_dmg2 = PhysicalDamageRecord(
        damage_code="BLG-DMG-002",
        road_segment_id=4, # College Road (Bogarves to Hindwadi)
        road_name="College Road (near Bogarves)",
        latitude=15.8525,
        longitude=74.4998,
        within_belagavi=True,
        category_code="D00",
        damage_type="Longitudinal Crack",
        verified_severity="Minor",
        verified_depth_tier="Shallow",
        verified_risk_score=28.0,
        priority_level="Low",
        verification_status="Verified",
        verified_by="Er. Rajesh Verma",
        verified_at=datetime.utcnow() - timedelta(days=13),
        evidence_photo_path="data/outputs/annotated_ring_road_oct.jpg",
        image_hash="b2c3d4e5f6071829",
        first_reported_date=datetime.utcnow() - timedelta(days=14),
        latest_inspection_date=datetime.utcnow() - timedelta(days=14),
        times_observed=1,
        repair_status="Pending",
        notes="Crack sealing scheduled for quarterly zonal maintenance."
    )
    db.add(p_dmg2)
    db.flush()
    d3_1.physical_damage_id = p_dmg2.id

    obs3 = DamageObservation(
        physical_damage_id=p_dmg2.id,
        submission_id=sub3.id,
        observation_date=datetime.utcnow() - timedelta(days=14),
        observed_severity="Minor",
        observed_area_pct=0.018,
        condition_state="Newly Detected",
        evidence_photo_path="data/outputs/annotated_ring_road_oct.jpg",
        observer_type="citizen",
        notes="First reported crack observation."
    )
    db.add(obs3)

    # ==========================================================================
    # SUBMISSION 4: NH-48 Bypass (Gandhi Nagar to Halaga) - Verified Repaired
    # ==========================================================================
    sub4 = Submission(
        code="INSP-BLG-202611-004",
        title="NH-48 Bypass Post-Patching Compliance Audit",
        submitter_type="authority",
        submitter_name="Er. Rajesh Verma",
        user_id=u_authority.id,
        media_type="image",
        file_path="data/uploads/nh48_survey_post_repair.jpg",
        annotated_path="data/outputs/annotated_nh48_survey_post_repair.jpg",
        thumbnail_path="data/outputs/annotated_nh48_survey_post_repair.jpg",
        upload_time=datetime.utcnow() - timedelta(days=3),
        road_name="NH-48 Belagavi Bypass (KM 504.2)",
        road_type="Highway",
        speed_limit=90,
        weather_condition="Clear/Dry",
        traffic_volume="High",
        description="Verification audit of contractor cold-patch bituminous overlay. Pavement smooth and defect-free.",
        latitude=15.8450,
        longitude=74.5550,
        location_name="NH-48 Belagavi Bypass, Gandhi Nagar",
        within_belagavi=True,
        total_detections=0,
        unique_defects_count=0,
        minor_count=0,
        moderate_count=0,
        severe_count=0,
        risk_score=5.0,
        risk_level="Low",
        status="Repair Completed"
    )
    db.add(sub4)
    db.flush()

    p_dmg3 = PhysicalDamageRecord(
        damage_code="BLG-DMG-003",
        road_segment_id=11, # NH-48 Bypass (Gandhi Nagar to Halaga)
        road_name="NH-48 Belagavi Bypass (Gandhi Nagar)",
        latitude=15.8450,
        longitude=74.5550,
        within_belagavi=True,
        category_code="D40",
        damage_type="Pothole (Repaired)",
        verified_severity="Minor",
        verified_depth_tier="Shallow",
        verified_risk_score=5.0,
        priority_level="Low",
        verification_status="Repaired",
        verified_by="Er. Rajesh Verma",
        verified_at=datetime.utcnow() - timedelta(days=3),
        evidence_photo_path="data/outputs/annotated_nh48_survey_post_repair.jpg",
        image_hash="c3d4e5f60718293a",
        first_reported_date=datetime.utcnow() - timedelta(days=30),
        latest_inspection_date=datetime.utcnow() - timedelta(days=3),
        times_observed=2,
        repair_status="Verified Closed",
        repair_verified_date=datetime.utcnow() - timedelta(days=3),
        notes="Bitumen overlay verified by municipal engineer. Safe for high-speed transit."
    )
    db.add(p_dmg3)
    db.flush()

    obs4 = DamageObservation(
        physical_damage_id=p_dmg3.id,
        submission_id=sub4.id,
        observation_date=datetime.utcnow() - timedelta(days=3),
        observed_severity="Repaired",
        observed_area_pct=0.0,
        condition_state="Repaired",
        evidence_photo_path="data/outputs/annotated_nh48_survey_post_repair.jpg",
        observer_type="authority",
        notes="Full patch compliance approved."
    )
    db.add(obs4)

    # Legacy Historical Comparison (sub1 vs sub4)
    comp = HistoricalComparison(
        location_name="Belagavi Highway Corridor",
        latitude=15.8450,
        longitude=74.5550,
        inspection_id_earlier=sub1.id,
        inspection_id_later=sub4.id,
        earlier_date=sub1.upload_time,
        later_date=sub4.upload_time,
        condition_trend="Repaired / Improved",
        earlier_defect_count=2,
        later_defect_count=0,
        area_delta_pct=-100.0,
        side_by_side_path="data/outputs/comparison_insp1_insp3.jpg",
        summary_notes="Full bitumen patch overlay verified on Belagavi Highway corridor."
    )
    db.add(comp)

    # ==========================================================================
    # SUBMISSION 5: Congress Road Video Survey (ByteTrack Demonstration)
    # ==========================================================================
    sub5 = Submission(
        code="INSP-BLG-VID-202611-005",
        title="Authority Video Survey: Congress Road to 1st Railway Gate",
        submitter_type="authority",
        submitter_name="PWD Survey Van #4",
        media_type="video",
        file_path="data/uploads/test_10mb_sample.mp4",
        annotated_path="data/outputs/tracked_6e03e55d.mp4",
        thumbnail_path="data/outputs/annotated_nh48_survey_jan.jpg",
        upload_time=datetime.utcnow() - timedelta(days=1),
        road_name="Congress Road (Camp to 1st Gate)",
        road_type="Arterial",
        speed_limit=50,
        weather_condition="Clear/Dry",
        traffic_volume="Moderate",
        description="Continuous dashcam video survey. Processed with ByteTrack frame association.",
        latitude=15.8485,
        longitude=74.5025,
        location_name="Congress Road, Belagavi",
        within_belagavi=True,
        total_detections=1,
        unique_defects_count=1,
        minor_count=0,
        moderate_count=1,
        severe_count=0,
        risk_score=42.0,
        risk_level="Moderate",
        status="Verified"
    )
    db.add(sub5)
    db.flush()

    d5_1 = AIDetection(
        submission_id=sub5.id,
        track_id="POTHOLE-003",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.875,
        bbox_x1=200.0, bbox_y1=250.0, bbox_x2=310.0, bbox_y2=340.0,
        relative_area=0.028,
        severity="Moderate",
        estimated_depth_tier="Medium",
        image_hash="e5f60718293a4b5c",
        latitude=15.8485,
        longitude=74.5025,
        verification_status="Verified"
    )
    db.add(d5_1)
    db.flush()

    p_dmg4 = PhysicalDamageRecord(
        damage_code="BLG-DMG-004",
        road_segment_id=3, # Congress Road
        road_name="Congress Road (near 1st Gate)",
        latitude=15.8485,
        longitude=74.5025,
        within_belagavi=True,
        category_code="D40",
        damage_type="Pothole",
        verified_severity="Moderate",
        verified_depth_tier="Medium",
        verified_risk_score=42.0,
        priority_level="Medium",
        verification_status="Verified",
        verified_by="Er. Rajesh Verma",
        verified_at=datetime.utcnow() - timedelta(hours=18),
        evidence_photo_path="data/outputs/annotated_nh48_survey_jan.jpg",
        image_hash="e5f60718293a4b5c",
        first_reported_date=datetime.utcnow() - timedelta(days=1),
        latest_inspection_date=datetime.utcnow() - timedelta(days=1),
        times_observed=1,
        repair_status="Pending",
        notes="Tracked continuously across 24 video frames. Unique defect verified."
    )
    db.add(p_dmg4)
    db.flush()
    d5_1.physical_damage_id = p_dmg4.id

    obs5 = DamageObservation(
        physical_damage_id=p_dmg4.id,
        submission_id=sub5.id,
        observation_date=datetime.utcnow() - timedelta(days=1),
        observed_severity="Moderate",
        observed_area_pct=0.028,
        condition_state="Newly Detected",
        evidence_photo_path="data/outputs/annotated_nh48_survey_jan.jpg",
        observer_type="authority",
        notes="Detected via ByteTrack video survey."
    )
    db.add(obs5)

    db.commit()
    db.close()
    print("[Belagavi Seeder] Seeding complete! Database synchronized to Belagavi, Karnataka.")

if __name__ == "__main__":
    seed_belagavi_database()
