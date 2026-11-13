"""
ROADVISION AI - SQLAlchemy ORM Models
Defines schemas for Inspections, Defects, Tracks, Duplicates, Risks, Repairs, and Comparisons.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    role = Column(String(20), default="inspector") # admin, inspector, contractor
    created_at = Column(DateTime, default=datetime.utcnow)

class Inspection(Base):
    __tablename__ = "inspections"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True) # e.g. INSP-2026-001
    title = Column(String(150), default="Road Condition Survey")
    media_type = Column(String(10), default="image") # "image" or "video"
    file_path = Column(String(300))
    annotated_path = Column(String(300))
    thumbnail_path = Column(String(300), nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    
    # Road metadata
    road_name = Column(String(150), default="Ring Road Expressway")
    road_type = Column(String(50), default="Arterial") # Highway, Arterial, Local, Residential
    speed_limit = Column(Integer, default=60) # km/h
    weather_condition = Column(String(50), default="Clear/Dry")
    traffic_volume = Column(String(50), default="Moderate") # Low, Moderate, High
    
    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(200), default="Sector 14, Main Corridor")
    
    # Metrics
    total_detections = Column(Integer, default=0)
    unique_defects_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    moderate_count = Column(Integer, default=0)
    severe_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0) # 0 to 100
    risk_level = Column(String(20), default="Low") # Low, Moderate, High, Critical
    
    status = Column(String(30), default="completed") # pending, processing, completed, failed
    notes = Column(Text, nullable=True)
    
    # Relationships
    defects = relationship("Defect", back_populates="inspection", cascade="all, delete-orphan")
    repairs = relationship("RepairRecord", back_populates="inspection", cascade="all, delete-orphan")

class Defect(Base):
    __tablename__ = "defects"
    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), index=True)
    track_id = Column(String(50), index=True) # e.g. POTHOLE-001, CRACK-002
    
    # AI Classification
    class_id = Column(Integer)
    class_name = Column(String(50)) # longitudinal_crack, transverse_crack, alligator_crack, pothole
    category_code = Column(String(10)) # D00, D10, D20, D40
    confidence = Column(Float)
    
    # Bounding Box (pixels normalized or absolute)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    relative_area = Column(Float, default=0.0) # area / image_area
    
    # Severity
    severity = Column(String(20), default="Minor") # Minor, Moderate, Severe
    estimated_depth_tier = Column(String(20), default="Shallow") # Shallow, Medium, Deep
    
    # Video Frame context
    frame_index = Column(Integer, default=0)
    timestamp_sec = Column(Float, default=0.0)
    
    # Geolocation & Image Hash
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_hash = Column(String(64), nullable=True) # Perceptual hash for duplicate matching
    
    # Human Verification & Audit
    verification_status = Column(String(30), default="Unverified") # Unverified, Verified, Rejected, Modified
    verified_class = Column(String(50), nullable=True)
    verified_severity = Column(String(20), nullable=True)
    verified_by = Column(String(50), nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    # Relationship
    inspection = relationship("Inspection", back_populates="defects")

class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"
    id = Column(Integer, primary_key=True, index=True)
    new_defect_id = Column(Integer, ForeignKey("defects.id"))
    existing_defect_id = Column(Integer, ForeignKey("defects.id"))
    spatial_distance_m = Column(Float)
    visual_similarity_pct = Column(Float)
    category_match = Column(Boolean, default=True)
    status = Column(String(30), default="Pending") # Pending, Confirmed_Duplicate, Dismissed, Merged
    created_at = Column(DateTime, default=datetime.utcnow)

class RepairRecord(Base):
    __tablename__ = "repair_records"
    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"))
    defect_id = Column(Integer, ForeignKey("defects.id"), nullable=True)
    
    # Lifecycle: Detected -> Reported -> Pending Verification -> Verified -> Assigned -> Repair in Progress -> Repaired -> Awaiting Final Verification -> Closed
    status = Column(String(50), default="Detected")
    priority = Column(String(20), default="Medium") # Low, Medium, High, Emergency
    assigned_authority = Column(String(100), default="Municipal Road Maintenance Division")
    assigned_contractor = Column(String(100), nullable=True)
    
    # Media & Evidence
    before_photo_path = Column(String(300), nullable=True)
    after_photo_path = Column(String(300), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_repair_date = Column(DateTime, nullable=True)
    repair_completed_date = Column(DateTime, nullable=True)
    verified_date = Column(DateTime, nullable=True)
    
    verified_by = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)
    
    inspection = relationship("Inspection", back_populates="repairs")

class HistoricalComparison(Base):
    __tablename__ = "historical_comparisons"
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(150))
    latitude = Column(Float)
    longitude = Column(Float)
    
    inspection_id_earlier = Column(Integer, ForeignKey("inspections.id"))
    inspection_id_later = Column(Integer, ForeignKey("inspections.id"))
    
    earlier_date = Column(DateTime)
    later_date = Column(DateTime)
    
    condition_trend = Column(String(30)) # "Worsened", "Stable", "Improved/Repaired"
    earlier_defect_count = Column(Integer, default=0)
    later_defect_count = Column(Integer, default=0)
    area_delta_pct = Column(Float, default=0.0) # +% increase or -% decrease
    
    side_by_side_path = Column(String(300), nullable=True)
    summary_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50)) # CREATE, VERIFY, REJECT, MERGE, REPAIR_UPDATE
    entity_type = Column(String(50)) # Inspection, Defect, Repair
    entity_id = Column(Integer)
    actor = Column(String(50), default="System AI")
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)
