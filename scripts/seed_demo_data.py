"""
ROADVISION AI - Realistic Demonstration Data Seeder
Populates the database with multi-location inspections, defects, duplicate matches,
repair workflows, and historical temporal surveys for national hackathon demonstration.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import cv2
import numpy as np
from datetime import datetime, timedelta

from backend.database import SessionLocal, init_db
from backend.models_db import Inspection, Defect, DuplicateMatch, RepairRecord, HistoricalComparison
from backend.config import UPLOADS_DIR, OUTPUTS_DIR
from backend.detector import compute_dhash
from backend.progress_monitor import generate_side_by_side_comparison

def create_synthetic_road_sample(filename, has_pothole=True, has_crack=True, repaired=False):
    h, w = 640, 640
    # Asphalt surface
    img = np.full((h, w, 3), 65, dtype=np.uint8)
    noise = np.random.normal(0, 14, (h, w, 3)).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Road lane lines
    cv2.line(img, (320, 0), (320, 640), (210, 210, 210), 6)

    annotated = img.copy()

    if repaired:
        # Asphalt patch (fresh dark bitumen)
        cv2.rectangle(img, (200, 280), (380, 440), (35, 35, 38), -1)
        cv2.rectangle(annotated, (200, 280), (380, 440), (35, 35, 38), -1)
        # Sealant perimeter line
        cv2.rectangle(annotated, (196, 276), (384, 444), (20, 20, 22), 3)
        cv2.putText(annotated, "REPAIRED / BITUMEN PATCH", (200, 265), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    else:
        if has_pothole:
            # Cavity
            cv2.ellipse(img, (260, 360), (75, 48), 15, 0, 360, (20, 20, 24), -1)
            cv2.ellipse(img, (255, 355), (60, 38), 15, 0, 360, (10, 10, 12), -1)

            cv2.ellipse(annotated, (260, 360), (75, 48), 15, 0, 360, (20, 20, 24), -1)
            cv2.rectangle(annotated, (180, 305), (340, 415), (0, 0, 255), 3)
            cv2.putText(annotated, "POTHOLE 91% [Severe]", (180, 295), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

        if has_crack:
            crack_pts = np.array([[440, 80], [450, 220], [435, 360], [455, 500], [445, 620]], np.int32)
            cv2.polylines(img, [crack_pts], False, (18, 18, 20), 4)

            cv2.polylines(annotated, [crack_pts], False, (18, 18, 20), 4)
            cv2.rectangle(annotated, (415, 75), (475, 625), (255, 100, 0), 2)
            cv2.putText(annotated, "Longitudinal Crack 84% [Moderate]", (220, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 100, 0), 2)

    in_path = os.path.join(UPLOADS_DIR, filename)
    out_path = os.path.join(OUTPUTS_DIR, "annotated_" + filename)
    cv2.imwrite(in_path, img)
    cv2.imwrite(out_path, annotated)
    return in_path, out_path

def seed_database():
    init_db()
    db = SessionLocal()

    # Clear existing records to ensure fresh state
    db.query(HistoricalComparison).delete()
    db.query(RepairRecord).delete()
    db.query(DuplicateMatch).delete()
    db.query(Defect).delete()
    db.query(Inspection).delete()
    db.commit()

    print("[Seeder] Generating sample road imagery and inspections...")

    # Inspection 1: High-risk Arterial Road (NH-48 Corridor)
    in1, out1 = create_synthetic_road_sample("nh48_survey_jan.jpg", has_pothole=True, has_crack=True)
    insp1 = Inspection(
        code="INSP-202611-001",
        title="NH-48 Gurugram-Delhi Express Highway",
        media_type="image",
        file_path=in1,
        annotated_path=out1,
        thumbnail_path=out1,
        upload_time=datetime.utcnow() - timedelta(days=28),
        road_name="NH-48 Corridor (KM 24.6)",
        road_type="Highway",
        speed_limit=90,
        weather_condition="Rainy/Wet",
        traffic_volume="High",
        latitude=28.4595,
        longitude=77.0266,
        location_name="Gurugram IFFCO Chowk Underpass",
        total_detections=2,
        unique_defects_count=2,
        minor_count=0,
        moderate_count=1,
        severe_count=1,
        risk_score=78.5,
        risk_level="Critical",
        status="completed"
    )
    db.add(insp1)
    db.flush()

    d1_1 = Defect(
        inspection_id=insp1.id,
        track_id="POTHOLE-001",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.912,
        bbox_x1=180, bbox_y1=305, bbox_x2=340, bbox_y2=415,
        relative_area=0.043,
        severity="Severe",
        estimated_depth_tier="Deep",
        image_hash=compute_dhash(cv2.imread(in1)[305:415, 180:340]),
        latitude=28.4595,
        longitude=77.0266,
        verification_status="Verified",
        verified_class="pothole",
        verified_severity="Severe",
        verified_by="Chief Highway Inspector"
    )
    d1_2 = Defect(
        inspection_id=insp1.id,
        track_id="CRACK-001",
        class_id=0,
        class_name="longitudinal_crack",
        category_code="D00",
        confidence=0.845,
        bbox_x1=415, bbox_y1=75, bbox_x2=475, bbox_y2=625,
        relative_area=0.032,
        severity="Moderate",
        estimated_depth_tier="Medium",
        image_hash="a1b2c3d4e5f60718",
        latitude=28.4595,
        longitude=77.0266,
        verification_status="Verified"
    )
    db.add_all([d1_1, d1_2])
    db.flush()

    # Repair Record for Inspection 1
    rep1 = RepairRecord(
        inspection_id=insp1.id,
        defect_id=d1_1.id,
        status="Repair in Progress",
        priority="Emergency",
        assigned_authority="National Highways Authority of India (NHAI)",
        assigned_contractor="L&T Infrastructure Maintenance Div",
        created_at=datetime.utcnow() - timedelta(days=26),
        scheduled_repair_date=datetime.utcnow() + timedelta(days=2),
        before_photo_path=out1,
        remarks="Emergency patch order dispatched due to high vehicular momentum on highway."
    )
    db.add(rep1)

    # Inspection 2: Duplicate Citizen Report (Same location, 8m away)
    in2, out2 = create_synthetic_road_sample("citizen_report_nh48.jpg", has_pothole=True, has_crack=False)
    insp2 = Inspection(
        code="INSP-202611-002",
        title="Citizen Mobile Report: Pothole NH-48",
        media_type="image",
        file_path=in2,
        annotated_path=out2,
        thumbnail_path=out2,
        upload_time=datetime.utcnow() - timedelta(days=20),
        road_name="NH-48 Corridor (KM 24.6)",
        road_type="Highway",
        speed_limit=90,
        weather_condition="Clear/Dry",
        traffic_volume="High",
        latitude=28.45955, # ~6 meters offset
        longitude=77.02664,
        location_name="Gurugram IFFCO Chowk Underpass",
        total_detections=1,
        unique_defects_count=1,
        minor_count=0,
        moderate_count=0,
        severe_count=1,
        risk_score=74.2,
        risk_level="High",
        status="completed"
    )
    db.add(insp2)
    db.flush()

    d2_1 = Defect(
        inspection_id=insp2.id,
        track_id="POTHOLE-002",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.887,
        bbox_x1=182, bbox_y1=308, bbox_x2=338, bbox_y2=412,
        relative_area=0.041,
        severity="Severe",
        estimated_depth_tier="Deep",
        image_hash=d1_1.image_hash, # Same visual hash
        latitude=28.45955,
        longitude=77.02664,
        verification_status="Unverified"
    )
    db.add(d2_1)
    db.flush()

    # Link as duplicate match
    dup1 = DuplicateMatch(
        new_defect_id=d2_1.id,
        existing_defect_id=d1_1.id,
        spatial_distance_m=6.8,
        visual_similarity_pct=98.5,
        category_match=True,
        status="Pending"
    )
    db.add(dup1)

    # Inspection 3: Subsequent temporal inspection showing Repair Completed!
    in3, out3 = create_synthetic_road_sample("nh48_survey_post_repair.jpg", repaired=True)
    insp3 = Inspection(
        code="INSP-202611-003",
        title="NH-48 Post-Repair Compliance Audit",
        media_type="image",
        file_path=in3,
        annotated_path=out3,
        thumbnail_path=out3,
        upload_time=datetime.utcnow() - timedelta(days=2),
        road_name="NH-48 Corridor (KM 24.6)",
        road_type="Highway",
        speed_limit=90,
        weather_condition="Clear/Dry",
        traffic_volume="High",
        latitude=28.4595,
        longitude=77.0266,
        location_name="Gurugram IFFCO Chowk Underpass",
        total_detections=0,
        unique_defects_count=0,
        minor_count=0,
        moderate_count=0,
        severe_count=0,
        risk_score=5.0,
        risk_level="Low",
        status="completed"
    )
    db.add(insp3)
    db.flush()

    # Historical Comparison (insp1 vs insp3)
    side_path = os.path.join(OUTPUTS_DIR, "comparison_insp1_insp3.jpg")
    generate_side_by_side_comparison(
        out1, out3, side_path,
        insp1.upload_time.strftime("%Y-%m-%d"),
        insp3.upload_time.strftime("%Y-%m-%d"),
        "Repaired / Improved"
    )

    comp = HistoricalComparison(
        location_name="NH-48 Corridor (KM 24.6)",
        latitude=28.4595,
        longitude=77.0266,
        inspection_id_earlier=insp1.id,
        inspection_id_later=insp3.id,
        earlier_date=insp1.upload_time,
        later_date=insp3.upload_time,
        condition_trend="Repaired / Improved",
        earlier_defect_count=2,
        later_defect_count=0,
        area_delta_pct=-100.0,
        side_by_side_path=side_path,
        summary_notes="Full bitumen patch overlay verified. Defect POTHOLE-001 eliminated and pavement restored."
    )
    db.add(comp)

    # Inspection 4: Ring Road Arterial (Deteriorating location)
    in4, out4 = create_synthetic_road_sample("ring_road_oct.jpg", has_pothole=False, has_crack=True)
    insp4 = Inspection(
        code="INSP-202611-004",
        title="Ring Road Lajpat Nagar Flyover Approach",
        media_type="image",
        file_path=in4,
        annotated_path=out4,
        thumbnail_path=out4,
        upload_time=datetime.utcnow() - timedelta(days=45),
        road_name="Inner Ring Road",
        road_type="Arterial",
        speed_limit=60,
        weather_condition="Clear/Dry",
        traffic_volume="High",
        latitude=28.5672,
        longitude=77.2435,
        location_name="Lajpat Nagar South Section",
        total_detections=1,
        unique_defects_count=1,
        minor_count=1,
        moderate_count=0,
        severe_count=0,
        risk_score=28.0,
        risk_level="Moderate",
        status="completed"
    )
    db.add(insp4)
    db.flush()

    d4_1 = Defect(
        inspection_id=insp4.id,
        track_id="CRACK-002",
        class_id=0,
        class_name="longitudinal_crack",
        category_code="D00",
        confidence=0.79,
        bbox_x1=400, bbox_y1=100, bbox_x2=450, bbox_y2=500,
        relative_area=0.019,
        severity="Minor",
        latitude=28.5672,
        longitude=77.2435,
        verification_status="Verified"
    )
    db.add(d4_1)

    # Inspection 5: Same Ring Road location 45 days later -> Worsened into Pothole!
    in5, out5 = create_synthetic_road_sample("ring_road_nov.jpg", has_pothole=True, has_crack=True)
    insp5 = Inspection(
        code="INSP-202611-005",
        title="Ring Road Lajpat Nagar (Re-survey)",
        media_type="image",
        file_path=in5,
        annotated_path=out5,
        thumbnail_path=out5,
        upload_time=datetime.utcnow() - timedelta(days=5),
        road_name="Inner Ring Road",
        road_type="Arterial",
        speed_limit=60,
        weather_condition="Rainy/Wet",
        traffic_volume="High",
        latitude=28.5672,
        longitude=77.2435,
        location_name="Lajpat Nagar South Section",
        total_detections=2,
        unique_defects_count=2,
        minor_count=0,
        moderate_count=1,
        severe_count=1,
        risk_score=71.2,
        risk_level="High",
        status="completed"
    )
    db.add(insp5)
    db.flush()

    d5_1 = Defect(
        inspection_id=insp5.id,
        track_id="POTHOLE-003",
        class_id=3,
        class_name="pothole",
        category_code="D40",
        confidence=0.89,
        bbox_x1=190, bbox_y1=310, bbox_x2=345, bbox_y2=420,
        relative_area=0.042,
        severity="Severe",
        latitude=28.5672,
        longitude=77.2435,
        verification_status="Unverified"
    )
    d5_2 = Defect(
        inspection_id=insp5.id,
        track_id="CRACK-003",
        class_id=0,
        class_name="longitudinal_crack",
        category_code="D00",
        confidence=0.82,
        bbox_x1=400, bbox_y1=80, bbox_x2=460, bbox_y2=580,
        relative_area=0.035,
        severity="Moderate",
        latitude=28.5672,
        longitude=77.2435,
        verification_status="Unverified"
    )
    db.add_all([d5_1, d5_2])
    db.flush()

    # Historical Comparison (insp4 vs insp5: WORSENED)
    side_path2 = os.path.join(OUTPUTS_DIR, "comparison_insp4_insp5.jpg")
    generate_side_by_side_comparison(
        out4, out5, side_path2,
        insp4.upload_time.strftime("%Y-%m-%d"),
        insp5.upload_time.strftime("%Y-%m-%d"),
        "Worsened"
    )

    comp2 = HistoricalComparison(
        location_name="Inner Ring Road (Lajpat Nagar)",
        latitude=28.5672,
        longitude=77.2435,
        inspection_id_earlier=insp4.id,
        inspection_id_later=insp5.id,
        earlier_date=insp4.upload_time,
        later_date=insp5.upload_time,
        condition_trend="Worsened",
        earlier_defect_count=1,
        later_defect_count=2,
        area_delta_pct=140.0,
        side_by_side_path=side_path2,
        summary_notes="Active deterioration: Crack progressed into severe structural pothole cavity under monsoon traffic."
    )
    db.add(comp2)

    db.commit()
    db.close()
    print("[Seeder] Successfully seeded 5 comprehensive road surveys across Delhi-NCR corridors!")

if __name__ == "__main__":
    seed_database()
