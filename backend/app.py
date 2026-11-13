"""
ROADVISION AI - Production FastAPI Backend Application
Exposes full REST API endpoints for detection, video tracking, duplicate detection,
risk assessment, repair lifecycle, historical comparisons, analytics, and reporting.
"""
import os
import shutil
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.config import (
    UPLOADS_DIR,
    OUTPUTS_DIR,
    REPORTS_DIR,
    RDD_CLASSES
)
from backend.database import get_db, init_db
from backend.models_db import (
    Inspection, Defect, DuplicateMatch, RepairRecord,
    HistoricalComparison, AuditLog, User
)
from backend.detector import detector
from backend.tracker import process_video_inspection
from backend.duplicate_engine import evaluate_duplicate_candidate
from backend.risk_engine import calculate_road_risk_score
from backend.progress_monitor import compare_inspections
from backend.report_generator import (
    generate_json_report, generate_csv_report, generate_html_report
)

app = FastAPI(
    title="ROADVISION AI",
    description="Intelligent Road Damage Detection, Tracking, Risk Prediction & Maintenance Platform",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static and media directories
BASE_PROJECT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_STATIC = os.path.join(BASE_PROJECT, "frontend", "static")
FRONTEND_TEMPLATES = os.path.join(BASE_PROJECT, "frontend", "templates")
DATA_DIR = os.path.join(BASE_PROJECT, "data")

app.mount("/static", StaticFiles(directory=FRONTEND_STATIC), name="static")
app.mount("/media/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/media/outputs", StaticFiles(directory=OUTPUTS_DIR), name="outputs")
app.mount("/media/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

@app.on_event("startup")
def startup_event():
    init_db()
    print("[ROADVISION AI] System started and database ready.")

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    index_file = os.path.join(FRONTEND_TEMPLATES, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ROADVISION AI Backend Active. Frontend index.html not yet built.</h1>"

@app.get("/roadguard", response_class=HTMLResponse)
def serve_roadguard_dashboard():
    rg_file = os.path.join(os.path.dirname(FRONTEND_TEMPLATES), "index_roadguard.html")
    if os.path.exists(rg_file):
        with open(rg_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>RoadGuard AI template not found.</h1>"

@app.get("/dashboard", response_class=HTMLResponse)
def serve_municipal_dashboard():
    dash_file = os.path.join(os.path.dirname(FRONTEND_TEMPLATES), "dashboard.html")
    if os.path.exists(dash_file):
        with open(dash_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ROADVISION AI Dashboard template not found.</h1>"

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ROADVISION AI",
        "models": {
            "primary": bool(detector.primary_model),
            "segmentation": bool(detector.alt_model),
            "primary_path": detector.primary_path,
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ==========================================
# 1. IMAGE INSPECTION ENDPOINT
# ==========================================
@app.post("/api/inspect/image")
async def inspect_image(
    file: UploadFile = File(...),
    road_name: str = Form("Ring Road Expressway"),
    road_type: str = Form("Arterial"),
    speed_limit: int = Form(60),
    weather: str = Form("Clear/Dry"),
    traffic: str = Form("Moderate"),
    manual_lat: Optional[float] = Form(None),
    manual_lon: Optional[float] = Form(None),
    conf_thresh: float = Form(0.20),
    model_choice: str = Form("ensemble"),
    db: Session = Depends(get_db)
):
    # Save input image
    ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    unique_id = uuid.uuid4().hex[:8]
    in_name = f"upload_{unique_id}{ext}"
    in_path = os.path.join(UPLOADS_DIR, in_name)

    with open(in_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run AI inference
    try:
        annotated_np, detections, (exif_lat, exif_lon) = detector.detect_image(
            in_path,
            conf_thresh=conf_thresh,
            model_choice=model_choice
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

    # Save annotated output
    out_name = f"annotated_{unique_id}.jpg"
    out_path = os.path.join(OUTPUTS_DIR, out_name)
    import cv2
    cv2.imwrite(out_path, annotated_np)

    final_lat = exif_lat if exif_lat is not None else manual_lat
    final_lon = exif_lon if exif_lon is not None else manual_lon

    # Compute risk score
    risk_score, risk_tier, risk_breakdown = calculate_road_risk_score(
        defects=detections,
        road_type=road_type,
        speed_limit=speed_limit,
        traffic_volume=traffic,
        weather_condition=weather
    )

    # Count severities
    minor_cnt = sum(1 for d in detections if d["severity"] == "Minor")
    mod_cnt = sum(1 for d in detections if d["severity"] == "Moderate")
    sev_cnt = sum(1 for d in detections if d["severity"] == "Severe")

    # Save inspection record
    insp_code = f"INSP-{datetime.utcnow().strftime('%Y%m%d')}-{unique_id.upper()}"
    inspection = Inspection(
        code=insp_code,
        title=f"Survey: {road_name}",
        media_type="image",
        file_path=in_path,
        annotated_path=out_path,
        thumbnail_path=out_path,
        road_name=road_name,
        road_type=road_type,
        speed_limit=speed_limit,
        weather_condition=weather,
        traffic_volume=traffic,
        latitude=final_lat,
        longitude=final_lon,
        location_name=road_name,
        total_detections=len(detections),
        unique_defects_count=len(detections),
        minor_count=minor_cnt,
        moderate_count=mod_cnt,
        severe_count=sev_cnt,
        risk_score=risk_score,
        risk_level=risk_tier,
        status="completed"
    )
    db.add(inspection)
    db.flush()

    # Save individual defects & check for duplicates
    saved_defects = []
    duplicate_candidates = []

    for det in detections:
        defect_obj = Defect(
            inspection_id=inspection.id,
            track_id=det["track_id"],
            class_id=det["class_id"],
            class_name=det["class_name"],
            category_code=det["category_code"],
            confidence=det["confidence"],
            bbox_x1=float(det["bbox"][0]),
            bbox_y1=float(det["bbox"][1]),
            bbox_x2=float(det["bbox"][2]),
            bbox_y2=float(det["bbox"][3]),
            relative_area=det["relative_area"],
            severity=det["severity"],
            estimated_depth_tier=det["depth_tier"],
            image_hash=det["image_hash"],
            latitude=final_lat,
            longitude=final_lon
        )
        db.add(defect_obj)
        db.flush()
        saved_defects.append(defect_obj)

        # Cross-inspection duplicate check against existing historical defects
        if final_lat and final_lon:
            prev_defects = db.query(Defect).filter(
                Defect.inspection_id != inspection.id,
                Defect.latitude.isnot(None),
                Defect.longitude.isnot(None)
            ).all()

            for prev in prev_defects:
                eval_res = evaluate_duplicate_candidate(defect_obj, prev)
                if eval_res["is_duplicate"] or eval_res["match_confidence"] >= 0.65:
                    dup = DuplicateMatch(
                        new_defect_id=defect_obj.id,
                        existing_defect_id=prev.id,
                        spatial_distance_m=eval_res["spatial_distance_m"],
                        visual_similarity_pct=eval_res["visual_similarity_pct"],
                        category_match=eval_res["category_match"],
                        status="Pending"
                    )
                    db.add(dup)
                    duplicate_candidates.append({
                        "new_defect_id": defect_obj.id,
                        "existing_defect_id": prev.id,
                        "distance_m": eval_res["spatial_distance_m"],
                        "visual_sim_pct": eval_res["visual_similarity_pct"],
                        "explanation": eval_res["explanation"]
                    })

    # Auto-generate repair record if severe or high risk
    if sev_cnt > 0 or risk_tier in ["High", "Critical"]:
        repair = RepairRecord(
            inspection_id=inspection.id,
            defect_id=saved_defects[0].id if saved_defects else None,
            status="Reported",
            priority="Emergency" if risk_tier == "Critical" else "High",
            assigned_authority="Municipal Public Works & Infrastructure Directorate",
            before_photo_path=out_path,
            remarks=f"Automated priority dispatch triggered: {sev_cnt} severe defects, Risk Index {risk_score}/100."
        )
        db.add(repair)

    db.commit()

    return {
        "status": "success",
        "inspection_id": inspection.id,
        "code": inspection.code,
        "media_type": "image",
        "annotated_url": f"/media/outputs/{out_name}",
        "original_url": f"/media/uploads/{in_name}",
        "total_detections": len(detections),
        "unique_defects": len(detections),
        "severity_summary": {"minor": minor_cnt, "moderate": mod_cnt, "severe": sev_cnt},
        "risk_score": risk_score,
        "risk_level": risk_tier,
        "risk_breakdown": risk_breakdown,
        "location": {"latitude": final_lat, "longitude": final_lon, "road_name": road_name},
        "defects": detections,
        "duplicate_warnings": duplicate_candidates
    }

# ==========================================
# 2. VIDEO INSPECTION & TRACKING ENDPOINT
# ==========================================
@app.post("/api/inspect/video")
async def inspect_video(
    file: UploadFile = File(...),
    road_name: str = Form("Outer Ring Roadway"),
    road_type: str = Form("Highway"),
    speed_limit: int = Form(80),
    weather: str = Form("Clear/Dry"),
    traffic: str = Form("Moderate"),
    manual_lat: Optional[float] = Form(28.6139),
    manual_lon: Optional[float] = Form(77.2090),
    conf_thresh: float = Form(0.15),
    stride: int = Form(3),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    unique_id = uuid.uuid4().hex[:8]
    in_name = f"video_{unique_id}{ext}"
    in_path = os.path.join(UPLOADS_DIR, in_name)

    with open(in_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    out_name = f"tracked_{unique_id}.mp4"
    out_path = os.path.join(OUTPUTS_DIR, out_name)

    try:
        tracking_result = process_video_inspection(
            video_path=in_path,
            output_video_path=out_path,
            conf_thresh=conf_thresh,
            sample_stride=stride
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video processing error: {str(e)}")

    tracked_defects = tracking_result["tracked_defects"]
    unique_summary = tracking_result["unique_summary"]

    # Compute risk score for unique defects
    risk_score, risk_tier, risk_breakdown = calculate_road_risk_score(
        defects=tracked_defects,
        road_type=road_type,
        speed_limit=speed_limit,
        traffic_volume=traffic,
        weather_condition=weather
    )

    insp_code = f"INSP-VID-{datetime.utcnow().strftime('%Y%m%d')}-{unique_id.upper()}"
    inspection = Inspection(
        code=insp_code,
        title=f"Video Survey: {road_name}",
        media_type="video",
        file_path=in_path,
        annotated_path=out_path,
        road_name=road_name,
        road_type=road_type,
        speed_limit=speed_limit,
        weather_condition=weather,
        traffic_volume=traffic,
        latitude=manual_lat,
        longitude=manual_lon,
        location_name=road_name,
        total_detections=tracking_result["total_frame_detections"],
        unique_defects_count=tracking_result["unique_defects_count"],
        minor_count=unique_summary.get("Minor", 0),
        moderate_count=unique_summary.get("Moderate", 0),
        severe_count=unique_summary.get("Severe", 0),
        risk_score=risk_score,
        risk_level=risk_tier,
        status="completed"
    )
    db.add(inspection)
    db.flush()

    # Save tracked defects to DB
    for tr in tracked_defects:
        bbox = tr["final_bbox"]
        defect_obj = Defect(
            inspection_id=inspection.id,
            track_id=tr["track_id"],
            class_id=0,
            class_name=tr["category_code"],
            category_code=tr["category_code"],
            confidence=tr["max_confidence"],
            bbox_x1=float(bbox[0]),
            bbox_y1=float(bbox[1]),
            bbox_x2=float(bbox[2]),
            bbox_y2=float(bbox[3]),
            relative_area=0.03,
            severity=tr["severity"],
            latitude=manual_lat,
            longitude=manual_lon
        )
        db.add(defect_obj)

    db.commit()

    return {
        "status": "success",
        "inspection_id": inspection.id,
        "code": inspection.code,
        "media_type": "video",
        "annotated_video_url": f"/media/outputs/{out_name}",
        "total_frames": tracking_result["total_frames"],
        "duration_sec": tracking_result["duration_sec"],
        "total_frame_detections": tracking_result["total_frame_detections"],
        "unique_defects_count": tracking_result["unique_defects_count"],
        "unique_summary": unique_summary,
        "risk_score": risk_score,
        "risk_level": risk_tier,
        "tracked_defects": tracked_defects
    }

# ==========================================
# 2B. DEDICATED VIDEO ANALYSIS DASHBOARD ENDPOINTS
# ==========================================
@app.post("/api/video/analyze")
async def analyze_video_dashboard(
    file: UploadFile = File(...),
    conf_thresh: float = Form(0.25),
    iou_thresh: float = Form(0.45),
    imgsz: int = Form(640),
    frame_skip: int = Form(2),
    road_name: str = Form("Survey Road"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Dedicated endpoint for dashcam video analysis with configurable inference settings:
    - Confidence threshold
    - IoU threshold
    - Input size (imgsz)
    - Nth frame skipping (frame_skip)
    Returns: Processed frames count, Total processing time / FPS, Unique damages count,
    Raw boxes count, Duplicates removed, Clip length, Damage timeline, and Severity mix.
    """
    t_start = datetime.utcnow()
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    unique_id = uuid.uuid4().hex[:8]
    in_name = f"video_{unique_id}{ext}"
    in_path = os.path.join(UPLOADS_DIR, in_name)

    with open(in_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    out_name = f"tracked_{unique_id}.mp4"
    out_path = os.path.join(OUTPUTS_DIR, out_name)

    try:
        tracking_result = process_video_inspection(
            video_path=in_path,
            output_video_path=out_path,
            conf_thresh=conf_thresh,
            iou_thresh=iou_thresh,
            sample_stride=max(1, frame_skip),
            imgsz=imgsz
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video analysis error: {str(e)}")

    elapsed = (datetime.utcnow() - t_start).total_seconds()
    proc_fps = round(tracking_result["processed_frames"] / elapsed, 1) if elapsed > 0 else 0.0

    insp_code = f"INSP-VID-{datetime.utcnow().strftime('%Y%m%d')}-{unique_id.upper()}"
    inspection = Inspection(
        code=insp_code,
        title=f"Video Analysis: {road_name}",
        media_type="video",
        file_path=in_path,
        annotated_path=out_path,
        road_name=road_name,
        road_type="Highway",
        speed_limit=60,
        weather_condition="Clear/Dry",
        traffic_volume="Moderate",
        latitude=lat or 15.3647,
        longitude=lng or 75.1240,
        location_name=road_name,
        total_detections=tracking_result["raw_boxes_count"],
        unique_defects_count=tracking_result["unique_damages"],
        minor_count=tracking_result["unique_summary"].get("Minor", 0),
        moderate_count=tracking_result["unique_summary"].get("Moderate", 0),
        severe_count=tracking_result["unique_summary"].get("Severe", 0),
        risk_score=min(100.0, tracking_result["unique_damages"] * 12.0),
        risk_level="High" if tracking_result["unique_damages"] >= 4 else ("Medium" if tracking_result["unique_damages"] >= 2 else "Low"),
        status="completed"
    )
    db.add(inspection)
    db.flush()

    for tr in tracking_result["tracked_defects"]:
        bbox = tr["final_bbox"]
        defect_obj = Defect(
            inspection_id=inspection.id,
            track_id=tr["track_id"],
            class_id=0,
            class_name=tr["category_code"],
            category_code=tr["category_code"],
            confidence=tr["max_confidence"],
            bbox_x1=float(bbox[0]),
            bbox_y1=float(bbox[1]),
            bbox_x2=float(bbox[2]),
            bbox_y2=float(bbox[3]),
            relative_area=0.03,
            severity=tr["severity"],
            latitude=lat or 15.3647,
            longitude=lng or 75.1240
        )
        db.add(defect_obj)
    db.commit()

    return {
        "status": "success",
        "video_id": unique_id,
        "inspection_id": inspection.id,
        "inspection_code": insp_code,
        "processed_frames": tracking_result["processed_frames"],
        "total_frames": tracking_result["total_frames"],
        "total_time_sec": round(elapsed, 2),
        "fps": proc_fps,
        "video_fps": tracking_result["fps"],
        "clip_length_sec": tracking_result["clip_length_sec"],
        "unique_damages": tracking_result["unique_damages"],
        "raw_boxes_count": tracking_result["raw_boxes_count"],
        "duplicates_removed": tracking_result["duplicates_removed"],
        "severity_mix": tracking_result["severity_mix"],
        "damage_timeline": tracking_result["damage_timeline"],
        "unique_damages_list": tracking_result["unique_damages_list"],
        "annotated_video_url": f"/media/outputs/{out_name}",
        "download_url": f"/api/video/download/{out_name}"
    }

@app.get("/api/video/download/{filename}")
def download_processed_video(filename: str):
    """Provides direct browser download of the processed/annotated video clip."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(OUTPUTS_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Processed video file not found")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=safe_filename,
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )

@app.post("/api/video/save")
async def save_video_analysis_record(
    video_id: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db)
):
    """
    Saves/updates geographical coordinates (lat, lng) and text notes
    for an existing video analysis in the database.
    """
    inspection = db.query(Inspection).filter(
        (Inspection.annotated_path.like(f"%{video_id}%")) | 
        (Inspection.file_path.like(f"%{video_id}%"))
    ).first()

    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection record not found for this video")

    inspection.latitude = lat
    inspection.longitude = lng
    if notes:
        inspection.road_name = notes
        inspection.location_name = notes

    # Update child defects coordinates
    db.query(Defect).filter(Defect.inspection_id == inspection.id).update({
        Defect.latitude: lat,
        Defect.longitude: lng
    })
    db.commit()

    return {
        "status": "success",
        "message": "Analysis record successfully saved to database.",
        "inspection_id": inspection.id,
        "code": inspection.code,
        "latitude": lat,
        "longitude": lng,
        "notes": notes
    }

# ==========================================
# 3. INSPECTIONS & DEFECTS QUERY ENDPOINTS
# ==========================================
@app.get("/api/inspections")
def get_inspections(
    media_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(Inspection)
    if media_type:
        query = query.filter(Inspection.media_type == media_type)
    if risk_level:
        query = query.filter(Inspection.risk_level == risk_level)

    inspections = query.order_by(desc(Inspection.upload_time)).limit(limit).all()

    items = []
    for ins in inspections:
        items.append({
            "id": ins.id,
            "code": ins.code,
            "title": ins.title,
            "media_type": ins.media_type,
            "upload_time": ins.upload_time.isoformat() if ins.upload_time else None,
            "road_name": ins.road_name,
            "road_type": ins.road_type,
            "latitude": ins.latitude,
            "longitude": ins.longitude,
            "total_detections": ins.total_detections,
            "unique_defects_count": ins.unique_defects_count,
            "minor_count": ins.minor_count,
            "moderate_count": ins.moderate_count,
            "severe_count": ins.severe_count,
            "risk_score": ins.risk_score,
            "risk_level": ins.risk_level,
            "annotated_url": f"/media/outputs/{os.path.basename(ins.annotated_path)}" if ins.annotated_path else None
        })
    return {"total": len(items), "inspections": items}

@app.get("/api/inspections/{insp_id}")
def get_inspection_detail(insp_id: int, db: Session = Depends(get_db)):
    ins = db.query(Inspection).filter(Inspection.id == insp_id).first()
    if not ins:
        raise HTTPException(status_code=404, detail="Inspection not found")

    defects = db.query(Defect).filter(Defect.inspection_id == ins.id).all()
    defect_list = []
    for d in defects:
        defect_list.append({
            "id": d.id,
            "track_id": d.track_id,
            "category_code": d.category_code,
            "class_name": d.class_name,
            "confidence": d.confidence,
            "severity": d.severity,
            "estimated_depth_tier": d.estimated_depth_tier,
            "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
            "relative_area": d.relative_area,
            "verification_status": d.verification_status,
            "latitude": d.latitude,
            "longitude": d.longitude
        })

    return {
        "id": ins.id,
        "code": ins.code,
        "title": ins.title,
        "media_type": ins.media_type,
        "upload_time": ins.upload_time.isoformat() if ins.upload_time else None,
        "road_name": ins.road_name,
        "road_type": ins.road_type,
        "speed_limit": ins.speed_limit,
        "weather": ins.weather_condition,
        "traffic": ins.traffic_volume,
        "latitude": ins.latitude,
        "longitude": ins.longitude,
        "total_detections": ins.total_detections,
        "unique_defects_count": ins.unique_defects_count,
        "minor_count": ins.minor_count,
        "moderate_count": ins.moderate_count,
        "severe_count": ins.severe_count,
        "risk_score": ins.risk_score,
        "risk_level": ins.risk_level,
        "annotated_url": f"/media/outputs/{os.path.basename(ins.annotated_path)}" if ins.annotated_path else None,
        "defects": defect_list
    }

@app.get("/api/defects")
def get_all_defects(
    category_code: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(Defect)
    if category_code:
        query = query.filter(Defect.category_code == category_code)
    if severity:
        query = query.filter(Defect.severity == severity)

    defects = query.order_by(desc(Defect.id)).limit(limit).all()
    res = []
    for d in defects:
        res.append({
            "id": d.id,
            "inspection_id": d.inspection_id,
            "track_id": d.track_id,
            "category_code": d.category_code,
            "class_name": d.class_name,
            "confidence": d.confidence,
            "severity": d.severity,
            "verification_status": d.verification_status,
            "latitude": d.latitude,
            "longitude": d.longitude
        })
    return {"total": len(res), "defects": res}

# ==========================================
# 4. MANUAL VERIFICATION ENDPOINT
# ==========================================
@app.post("/api/defects/{defect_id}/verify")
def verify_defect(
    defect_id: int,
    action: str = Form("Verified"), # "Verified", "Rejected", "Modified"
    verified_class: Optional[str] = Form(None),
    verified_severity: Optional[str] = Form(None),
    reviewer: str = Form("Senior Municipal Engineer"),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    defect = db.query(Defect).filter(Defect.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")

    defect.verification_status = action
    if verified_class:
        defect.verified_class = verified_class
    if verified_severity:
        defect.verified_severity = verified_severity
    defect.verified_by = reviewer
    defect.verification_notes = notes
    defect.verified_at = datetime.utcnow()

    # Log audit
    audit = AuditLog(
        action=f"DEFECT_{action.upper()}",
        entity_type="Defect",
        entity_id=defect.id,
        actor=reviewer,
        details=f"Status set to {action}. Notes: {notes}"
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "defect_id": defect.id,
        "verification_status": defect.verification_status,
        "verified_by": defect.verified_by,
        "verified_at": defect.verified_at.isoformat()
    }

# ==========================================
# 5. DUPLICATES ENDPOINT
# ==========================================
@app.get("/api/duplicates")
def get_duplicates(db: Session = Depends(get_db)):
    matches = db.query(DuplicateMatch).filter(DuplicateMatch.status == "Pending").all()
    results = []
    for m in matches:
        d_new = db.query(Defect).filter(Defect.id == m.new_defect_id).first()
        d_old = db.query(Defect).filter(Defect.id == m.existing_defect_id).first()
        if d_new and d_old:
            results.append({
                "match_id": m.id,
                "new_defect": {
                    "id": d_new.id,
                    "track_id": d_new.track_id,
                    "category": d_new.category_code,
                    "severity": d_new.severity,
                    "inspection_id": d_new.inspection_id
                },
                "existing_defect": {
                    "id": d_old.id,
                    "track_id": d_old.track_id,
                    "category": d_old.category_code,
                    "severity": d_old.severity,
                    "inspection_id": d_old.inspection_id
                },
                "spatial_distance_m": m.spatial_distance_m,
                "visual_similarity_pct": m.visual_similarity_pct,
                "status": m.status
            })
    return {"total": len(results), "duplicates": results}

@app.post("/api/duplicates/{match_id}/resolve")
def resolve_duplicate(
    match_id: int,
    action: str = Form("Merged"), # "Merged" or "Dismissed"
    db: Session = Depends(get_db)
):
    m = db.query(DuplicateMatch).filter(DuplicateMatch.id == match_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Duplicate record not found")

    m.status = action
    db.commit()
    return {"status": "success", "match_id": match_id, "resolved_as": action}

# ==========================================
# 6. REPAIR LIFECYCLE MANAGEMENT ENDPOINTS
# ==========================================
@app.get("/api/repairs")
def get_repairs(status: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RepairRecord)
    if status:
        query = query.filter(RepairRecord.status == status)

    repairs = query.order_by(desc(RepairRecord.created_at)).all()
    res = []
    for r in repairs:
        res.append({
            "id": r.id,
            "inspection_id": r.inspection_id,
            "defect_id": r.defect_id,
            "status": r.status,
            "priority": r.priority,
            "assigned_authority": r.assigned_authority,
            "assigned_contractor": r.assigned_contractor,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "scheduled_date": r.scheduled_repair_date.isoformat() if r.scheduled_repair_date else None,
            "completed_date": r.repair_completed_date.isoformat() if r.repair_completed_date else None,
            "verified_by": r.verified_by,
            "remarks": r.remarks,
            "before_photo": f"/media/outputs/{os.path.basename(r.before_photo_path)}" if r.before_photo_path else None,
            "after_photo": f"/media/outputs/{os.path.basename(r.after_photo_path)}" if r.after_photo_path else None
        })
    return {"total": len(res), "repairs": res}

@app.post("/api/repairs/{repair_id}/update")
def update_repair(
    repair_id: int,
    status: str = Form(...), # Detected -> Reported -> Pending Verification -> Verified -> Assigned -> Repair in Progress -> Repaired -> Awaiting Final Verification -> Closed
    contractor: Optional[str] = Form(None),
    remarks: Optional[str] = Form(None),
    verified_by: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    r = db.query(RepairRecord).filter(RepairRecord.id == repair_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Repair record not found")

    r.status = status
    if contractor:
        r.assigned_contractor = contractor
    if remarks:
        r.remarks = remarks
    if verified_by:
        r.verified_by = verified_by

    if status in ["Repaired", "Closed"]:
        r.repair_completed_date = datetime.utcnow()
    if status == "Closed":
        r.verified_date = datetime.utcnow()

    db.commit()
    return {"status": "success", "repair_id": repair_id, "new_status": status}

# ==========================================
# 7. HISTORICAL PROGRESSION COMPARISON
# ==========================================
@app.post("/api/historical/compare")
def compare_temporal_inspections(
    earlier_insp_id: int = Form(...),
    later_insp_id: int = Form(...),
    db: Session = Depends(get_db)
):
    insp1 = db.query(Inspection).filter(Inspection.id == earlier_insp_id).first()
    insp2 = db.query(Inspection).filter(Inspection.id == later_insp_id).first()

    if not insp1 or not insp2:
        raise HTTPException(status_code=404, detail="One or both inspections not found")

    def1 = db.query(Defect).filter(Defect.inspection_id == insp1.id).all()
    def2 = db.query(Defect).filter(Defect.inspection_id == insp2.id).all()

    res = compare_inspections(insp1, insp2, def1, def2)

    # Save comparison record
    comp = HistoricalComparison(
        location_name=insp2.road_name,
        latitude=insp2.latitude or 0.0,
        longitude=insp2.longitude or 0.0,
        inspection_id_earlier=insp1.id,
        inspection_id_later=insp2.id,
        earlier_date=insp1.upload_time,
        later_date=insp2.upload_time,
        condition_trend=res["condition_trend"],
        earlier_defect_count=res["earlier_defect_count"],
        later_defect_count=res["later_defect_count"],
        area_delta_pct=res["area_delta_pct"],
        side_by_side_path=res["side_by_side_path"],
        summary_notes=res["summary_notes"]
    )
    db.add(comp)
    db.commit()

    return {
        "status": "success",
        "comparison_id": comp.id,
        "location": insp2.road_name,
        "trend": res["condition_trend"],
        "days_elapsed": res["days_elapsed"],
        "earlier_defects": res["earlier_defect_count"],
        "later_defects": res["later_defect_count"],
        "count_delta": res["count_delta"],
        "area_delta_pct": res["area_delta_pct"],
        "summary": res["summary_notes"],
        "side_by_side_url": f"/media/outputs/{os.path.basename(res['side_by_side_path'])}" if res["side_by_side_path"] else None
    }

# ==========================================
# 8. ANALYTICS & KPI METRICS
# ==========================================
@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db)):
    total_inspections = db.query(func.count(Inspection.id)).scalar() or 0
    total_defects = db.query(func.count(Defect.id)).scalar() or 0
    total_potholes = db.query(func.count(Defect.id)).filter(Defect.category_code == "D40").scalar() or 0

    minor_count = db.query(func.count(Defect.id)).filter(Defect.severity == "Minor").scalar() or 0
    moderate_count = db.query(func.count(Defect.id)).filter(Defect.severity == "Moderate").scalar() or 0
    severe_count = db.query(func.count(Defect.id)).filter(Defect.severity == "Severe").scalar() or 0

    critical_risk_locs = db.query(func.count(Inspection.id)).filter(Inspection.risk_level == "Critical").scalar() or 0
    high_risk_locs = db.query(func.count(Inspection.id)).filter(Inspection.risk_level == "High").scalar() or 0

    pending_repairs = db.query(func.count(RepairRecord.id)).filter(RepairRecord.status.in_(["Detected", "Reported", "Assigned", "Repair in Progress"])).scalar() or 0
    completed_repairs = db.query(func.count(RepairRecord.id)).filter(RepairRecord.status.in_(["Repaired", "Closed"])).scalar() or 0

    # Category breakdown
    cat_counts = {
        "D00": db.query(func.count(Defect.id)).filter(Defect.category_code == "D00").scalar() or 0,
        "D10": db.query(func.count(Defect.id)).filter(Defect.category_code == "D10").scalar() or 0,
        "D20": db.query(func.count(Defect.id)).filter(Defect.category_code == "D20").scalar() or 0,
        "D40": total_potholes
    }

    # Recent inspections
    recent = db.query(Inspection).order_by(desc(Inspection.upload_time)).limit(5).all()
    recent_list = []
    for r in recent:
        recent_list.append({
            "id": r.id,
            "code": r.code,
            "road_name": r.road_name,
            "media_type": r.media_type,
            "unique_defects": r.unique_defects_count,
            "risk_score": r.risk_score,
            "risk_level": r.risk_level,
            "date": r.upload_time.strftime("%Y-%m-%d %H:%M") if r.upload_time else "N/A"
        })

    return {
        "kpis": {
            "total_inspections": total_inspections,
            "total_defects": total_defects,
            "unique_potholes": total_potholes,
            "minor_damage": minor_count,
            "moderate_damage": moderate_count,
            "severe_damage": severe_count,
            "critical_risk_locations": critical_risk_locs,
            "high_risk_locations": high_risk_locs,
            "repairs_in_progress": pending_repairs,
            "verified_repairs": completed_repairs
        },
        "category_distribution": cat_counts,
        "severity_distribution": {
            "Minor": minor_count,
            "Moderate": moderate_count,
            "Severe": severe_count
        },
        "recent_inspections": recent_list
    }

# ==========================================
# 9. REPORT EXPORT ENDPOINT
# ==========================================
@app.get("/api/reports/{insp_id}/export/{fmt}")
def export_report(insp_id: int, fmt: str, db: Session = Depends(get_db)):
    ins = db.query(Inspection).filter(Inspection.id == insp_id).first()
    if not ins:
        raise HTTPException(status_code=404, detail="Inspection not found")

    defects = db.query(Defect).filter(Defect.inspection_id == ins.id).all()

    if fmt == "json":
        path = generate_json_report(ins, defects)
        return FileResponse(path, media_type="application/json", filename=os.path.basename(path))
    elif fmt == "csv":
        path = generate_csv_report(ins, defects)
        return FileResponse(path, media_type="text/csv", filename=os.path.basename(path))
    elif fmt in ["pdf", "html"]:
        path = generate_html_report(ins, defects)
        return FileResponse(path, media_type="text/html", filename=os.path.basename(path))
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json', 'csv', or 'pdf'")

# ==========================================
# 10. MODEL BENCHMARK METRICS ENDPOINT
# ==========================================
@app.get("/api/models/benchmark")
def get_model_benchmark():
    benchmark_json = os.path.join(BASE_PROJECT, "models", "benchmark", "benchmark_results.json")
    if os.path.exists(benchmark_json):
        import json
        with open(benchmark_json) as f:
            return json.load(f)
    return {"message": "Benchmark not yet executed"}
