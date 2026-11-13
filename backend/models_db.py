"""
ROADVISION AI - Central Geographical & Infrastructure Database Models
Primary Geographical Scope: Belagavi, Karnataka, India.

Strictly separates three distinct data states:
1. SUBMITTED: Original citizen reports and authority survey submissions (raw media, GPS, notes).
2. AI-GENERATED: Unverified deep-learning predictions (bounding boxes, class, confidence, preliminary risk).
3. VERIFIED: Authority-approved official physical damage records (verified category, severity, risk).
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.database import Base

# ==============================================================================
# 1. USER & AUTHORITY IDENTITY MANAGEMENT
# ==============================================================================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    name = Column(String(100), default="Citizen Reporter")
    role = Column(String(20), default="citizen") # "citizen", "authority", "contractor"
    department = Column(String(100), nullable=True) # e.g. "Belagavi City Corporation PWD"
    created_at = Column(DateTime, default=datetime.utcnow)

# ==============================================================================
# 2. BELAGAVI ROAD NETWORK SEGMENTS
# ==============================================================================
class RoadSegment(Base):
    __tablename__ = "road_segments"
    id = Column(Integer, primary_key=True, index=True)
    segment_code = Column(String(30), unique=True, index=True) # e.g. "BLG-SEG-01"
    name = Column(String(150), index=True) # e.g. "Khanapur Road (Tilakwadi - 3rd Gate)"
    location = Column(String(200), default="Belagavi, Karnataka")
    road_type = Column(String(50), default="Arterial") # Highway, Arterial, Local, Residential
    speed_limit = Column(Integer, default=60) # km/h
    from_node = Column(String(50), nullable=True)
    to_node = Column(String(50), nullable=True)
    start_lat = Column(Float, nullable=True)
    start_lon = Column(Float, nullable=True)
    end_lat = Column(Float, nullable=True)
    end_lon = Column(Float, nullable=True)
    length_m = Column(Float, default=0.0)
    geometry_geojson = Column(Text, nullable=True) # JSON coordinates string
    surface_type = Column(String(50), default="Bituminous Asphalt")

    # Official Road Condition & Health Metrics
    potholes_count = Column(Integer, default=0)
    total_damage_count = Column(Integer, default=0)
    condition_percentage = Column(Float, default=95.0) # 0.0 - 100.0 (Higher is healthier)
    risk_classification = Column(String(20), default="SAFE") # "SAFE", "MODERATE", "RISKY"
    inspection_source = Column(String(50), default="Demonstration Sample") # "Demonstration Sample", "Authority Inspection", "Verified Citizen Report"
    verification_status = Column(String(30), default="VERIFIED") # "VERIFIED", "PENDING"
    last_inspected_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    physical_defects = relationship("PhysicalDamageRecord", back_populates="road_segment")
    inspection_history = relationship("RoadInspectionHistory", back_populates="road_segment", cascade="all, delete-orphan", order_by="desc(RoadInspectionHistory.inspection_date)")


class RoadInspectionHistory(Base):
    __tablename__ = "road_inspection_history"
    id = Column(Integer, primary_key=True, index=True)
    road_segment_id = Column(Integer, ForeignKey("road_segments.id"), index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    inspection_date = Column(DateTime, default=datetime.utcnow)
    potholes_count = Column(Integer, default=0)
    total_damage_count = Column(Integer, default=0)
    condition_percentage = Column(Float, default=100.0)
    risk_classification = Column(String(20), default="SAFE") # "SAFE", "MODERATE", "RISKY"
    inspection_source = Column(String(50), default="Authority Inspection") # "Authority Inspection", "Verified Citizen Report", "Demonstration Sample"
    inspector_name = Column(String(100), default="Civil Road Authority")
    notes = Column(Text, nullable=True)

    # Relationships
    road_segment = relationship("RoadSegment", back_populates="inspection_history")
    submission = relationship("Submission")

# ==============================================================================
# 3. STATE 1: SUBMISSIONS (CITIZEN REPORTS & AUTHORITY INSPECTIONS)
# ==============================================================================
class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(35), unique=True, index=True) # e.g. "CIT-202611-001" or "INSP-202611-001"
    title = Column(String(150), default="Road Condition Survey")
    submitter_type = Column(String(20), default="citizen") # "citizen" or "authority"
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitter_name = Column(String(100), default="Public Citizen")
    media_type = Column(String(15), default="image") # "image" or "video"
    file_path = Column(String(300)) # Stored media path
    annotated_path = Column(String(300), nullable=True)
    thumbnail_path = Column(String(300), nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)

    # Location Metadata (Belagavi Scope)
    road_name = Column(String(150), default="Khanapur Road, Belagavi")
    road_type = Column(String(50), default="Arterial")
    speed_limit = Column(Integer, default=60)
    weather_condition = Column(String(50), default="Clear/Dry")
    traffic_volume = Column(String(50), default="Moderate")
    description = Column(Text, nullable=True) # Citizen grievance notes or authority directive

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_name = Column(String(200), default="Belagavi City")
    within_belagavi = Column(Boolean, default=True)

    # Preliminary AI-calculated summary metrics (State 2 summary)
    total_detections = Column(Integer, default=0)
    unique_defects_count = Column(Integer, default=0)
    potholes_count = Column(Integer, default=0)
    minor_count = Column(Integer, default=0)
    moderate_count = Column(Integer, default=0)
    severe_count = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0) # Preliminary AI risk
    risk_level = Column(String(20), default="Low")
    condition_percentage = Column(Float, default=100.0)
    risk_classification = Column(String(20), default="SAFE") # "SAFE", "MODERATE", "RISKY"
    road_segment_id = Column(Integer, ForeignKey("road_segments.id"), nullable=True)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), nullable=True)
    duplicate_status = Column(String(35), default="Unique") # "Unique", "Confirmed_Duplicate", "Needs_Verification", "Resolved_Duplicate"

    # Lifecycle Status:
    # "Pending Verification", "ACCEPTED", "REJECTED", "Verified", "Submitted", "Duplicate"
    status = Column(String(35), default="Pending Verification")
    notes = Column(Text, nullable=True)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Relationships
    ai_detections = relationship("AIDetection", back_populates="submission", cascade="all, delete-orphan")
    observations = relationship("DamageObservation", back_populates="submission")
    repairs = relationship("RepairRecord", back_populates="submission")
    physical_damage = relationship("PhysicalDamageRecord", foreign_keys=[physical_damage_id], back_populates="submissions")

# Backward Compatibility Alias for legacy code & tests
Inspection = Submission

# ==============================================================================
# 4. STATE 2: AI-GENERATED DETECTIONS & TRACKS (UNVERIFIED)
# ==============================================================================
class AIDetection(Base):
    __tablename__ = "ai_detections"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), index=True)
    track_id = Column(String(50), index=True) # Persistent video ID: e.g. "POTHOLE-001"

    # AI Model Prediction
    class_id = Column(Integer)
    class_name = Column(String(50)) # "pothole", "longitudinal_crack", "transverse_crack", "alligator_crack"
    category_code = Column(String(10)) # D00, D10, D20, D40
    confidence = Column(Float)

    # Bounding Box Coordinates
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    relative_area = Column(Float, default=0.0)

    # Preliminary AI Severity
    severity = Column(String(20), default="Minor") # Preliminary AI
    estimated_depth_tier = Column(String(20), default="Shallow")

    # Video Frame Context
    frame_index = Column(Integer, default=0)
    timestamp_sec = Column(Float, default=0.0)

    # Location & Perceptual Visual Hash
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    image_hash = Column(String(64), nullable=True)
    image_embedding = Column(Text, nullable=True) # JSON float array for deep visual similarity

    # Link to Verified Physical Damage (Once confirmed by Authority)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), nullable=True)

    # Verification Status: "Unverified", "Verified", "Rejected", "Modified"
    verification_status = Column(String(30), default="Unverified")
    verified_class = Column(String(50), nullable=True)
    verified_severity = Column(String(20), nullable=True)
    verified_by = Column(String(50), nullable=True)
    verification_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="ai_detections")
    physical_damage = relationship("PhysicalDamageRecord", back_populates="detections")

    # Backward compatibility property
    @property
    def inspection_id(self):
        return self.submission_id

    @inspection_id.setter
    def inspection_id(self, val):
        self.submission_id = val

# Backward Compatibility Alias
Defect = AIDetection

# ==============================================================================
# 5. STATE 3: VERIFIED PHYSICAL ROAD DAMAGE RECORDS
# ==============================================================================
class PhysicalDamageRecord(Base):
    __tablename__ = "physical_damage_records"
    id = Column(Integer, primary_key=True, index=True)
    damage_code = Column(String(35), unique=True, index=True) # e.g. "BLG-DMG-001"
    road_segment_id = Column(Integer, ForeignKey("road_segments.id"), nullable=True, index=True)
    road_name = Column(String(150), default="Khanapur Road, Belagavi")

    # Official Location
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    within_belagavi = Column(Boolean, default=True)

    # Verified Distress Characteristics
    category_code = Column(String(10), default="D40") # D00, D10, D20, D40
    damage_type = Column(String(50), default="Pothole")
    verified_severity = Column(String(20), default="Minor") # "Minor", "Moderate", "Severe"
    verified_depth_tier = Column(String(20), default="Shallow") # "Shallow", "Medium", "Deep"
    verified_risk_score = Column(Float, default=20.0) # 0 to 100 explainable score
    priority_level = Column(String(20), default="Low") # "Low", "Medium", "High", "Critical"

    # Official Authority Verification
    verification_status = Column(String(35), default="Verified") # "Unverified", "Verified", "Rejected", "Repaired", "Closed"
    verified_by = Column(String(100), default="Belagavi Municipal Road Engineer")
    verified_at = Column(DateTime, default=datetime.utcnow)

    # Media & Visual Hash of Physical Defect
    evidence_photo_path = Column(String(300), nullable=True)
    image_hash = Column(String(64), nullable=True)
    image_embedding = Column(Text, nullable=True) # JSON float array

    # Temporal & Historical Tracking
    first_reported_date = Column(DateTime, default=datetime.utcnow)
    latest_inspection_date = Column(DateTime, default=datetime.utcnow)
    times_observed = Column(Integer, default=1)

    # Repair Lifecycle Status
    repair_status = Column(String(35), default="Pending") # "Pending", "Assigned", "Repair in Progress", "Repaired", "Verified Closed"
    repair_verified_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    road_segment = relationship("RoadSegment", back_populates="physical_defects")
    detections = relationship("AIDetection", back_populates="physical_damage")
    observations = relationship("DamageObservation", back_populates="physical_damage", cascade="all, delete-orphan")
    repairs = relationship("RepairRecord", back_populates="physical_damage")
    submissions = relationship("Submission", foreign_keys="Submission.physical_damage_id", back_populates="physical_damage")
    duplicate_matches = relationship("DuplicateMatch", foreign_keys="DuplicateMatch.physical_damage_id")

# ==============================================================================
# 6. HISTORICAL TIME-SERIES DAMAGE OBSERVATIONS
# ==============================================================================
class DamageObservation(Base):
    __tablename__ = "damage_observations"
    id = Column(Integer, primary_key=True, index=True)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    observation_date = Column(DateTime, default=datetime.utcnow)

    # Observed State
    observed_severity = Column(String(20), default="Minor")
    observed_area_pct = Column(Float, default=0.0)
    # Condition Evolution:
    # "Newly Detected", "Unchanged", "Worsened", "Improving", "Repaired", "Reappeared"
    condition_state = Column(String(30), default="Newly Detected")
    evidence_photo_path = Column(String(300), nullable=True)
    observer_type = Column(String(20), default="citizen") # "citizen" or "authority"
    notes = Column(Text, nullable=True)

    # Relationships
    physical_damage = relationship("PhysicalDamageRecord", back_populates="observations")
    submission = relationship("Submission", back_populates="observations")

# ==============================================================================
# 7. DUPLICATE REPORT ENGINE CANDIDATES & RESOLUTIONS
# ==============================================================================
class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"
    id = Column(Integer, primary_key=True, index=True)
    new_defect_id = Column(Integer, ForeignKey("ai_detections.id"), nullable=True)
    existing_defect_id = Column(Integer, ForeignKey("ai_detections.id"), nullable=True)

    # Associated Physical Damage Asset & Submission
    candidate_submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), nullable=True)

    # Detailed Multi-Signal Metrics
    spatial_distance_m = Column(Float)
    visual_similarity_pct = Column(Float)
    embedding_similarity_pct = Column(Float, default=0.0)
    overall_matching_score = Column(Float, default=0.0)
    category_match = Column(Boolean, default=True)

    # Duplicate Classification State:
    # "Confirmed_Duplicate", "Needs_Verification", "New_Damage", "Marked_Separate", "Rejected"
    decision_status = Column(String(35), default="Needs_Verification")
    decision_reason = Column(Text, nullable=True)
    candidate_photo_path = Column(String(300), nullable=True)
    existing_photo_path = Column(String(300), nullable=True)

    # Lifecycle Status: "Pending", "Confirmed_Duplicate", "Dismissed", "Merged", "Rejected"
    status = Column(String(35), default="Pending")
    resolution_notes = Column(Text, nullable=True)
    resolved_by = Column(String(50), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate_submission = relationship("Submission", foreign_keys=[candidate_submission_id])
    physical_damage = relationship("PhysicalDamageRecord", foreign_keys=[physical_damage_id], overlaps="duplicate_matches")
    new_defect = relationship("AIDetection", foreign_keys=[new_defect_id])
    existing_defect = relationship("AIDetection", foreign_keys=[existing_defect_id])

# ==============================================================================
# 8. AUTHORITY MANUAL VERIFICATION & CORRECTION AUDIT TRAIL
# ==============================================================================
class VerificationAudit(Base):
    __tablename__ = "verification_audits"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    defect_id = Column(Integer, ForeignKey("ai_detections.id"), nullable=True)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), nullable=True)

    # Preserves original AI prediction vs authority-corrected prediction
    original_category = Column(String(20), nullable=True)
    original_severity = Column(String(20), nullable=True)
    original_bbox = Column(Text, nullable=True) # JSON coordinates
    original_risk_score = Column(Float, nullable=True)

    corrected_category = Column(String(20), nullable=True)
    corrected_severity = Column(String(20), nullable=True)
    corrected_bbox = Column(Text, nullable=True)
    corrected_risk_score = Column(Float, nullable=True)

    action = Column(String(30), default="Approved") # "Approved", "Rejected", "Modified"
    auditor_name = Column(String(100), default="Belagavi City Engineer")
    audit_timestamp = Column(DateTime, default=datetime.utcnow)
    comments = Column(Text, nullable=True)

# Backward Compatibility Alias
AuditLog = VerificationAudit

# ==============================================================================
# 9. MUNICIPAL REPAIR LIFECYCLE & EVIDENCE VERIFICATION
# ==============================================================================
class RepairRecord(Base):
    __tablename__ = "repair_records"
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=True)
    defect_id = Column(Integer, ForeignKey("ai_detections.id"), nullable=True)
    physical_damage_id = Column(Integer, ForeignKey("physical_damage_records.id"), nullable=True)

    # Lifecycle:
    # "Detected" -> "Reported" -> "Pending Verification" -> "Assigned" -> "Repair in Progress" -> "Repaired" -> "Verified Closed"
    status = Column(String(50), default="Assigned")
    priority = Column(String(20), default="Medium") # "Low", "Medium", "High", "Emergency"
    assigned_authority = Column(String(100), default="Belagavi City Corporation (PWD)")
    assigned_contractor = Column(String(100), nullable=True)
    
    # Before and After Evidence
    before_photo_path = Column(String(300), nullable=True)
    after_photo_path = Column(String(300), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_repair_date = Column(DateTime, nullable=True)
    repair_completed_date = Column(DateTime, nullable=True)
    verified_date = Column(DateTime, nullable=True)
    verified_by = Column(String(50), nullable=True)
    remarks = Column(Text, nullable=True)

    # Relationships
    submission = relationship("Submission", back_populates="repairs")
    physical_damage = relationship("PhysicalDamageRecord", back_populates="repairs")

    # Backward compatibility property
    @property
    def inspection_id(self):
        return self.submission_id

    @inspection_id.setter
    def inspection_id(self, val):
        self.submission_id = val

# Backward Compatibility Alias for legacy code & tests
class HistoricalComparison(Base):
    __tablename__ = "historical_comparisons"
    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(150))
    latitude = Column(Float)
    longitude = Column(Float)
    inspection_id_earlier = Column(Integer, ForeignKey("submissions.id"))
    inspection_id_later = Column(Integer, ForeignKey("submissions.id"))
    earlier_date = Column(DateTime)
    later_date = Column(DateTime)
    condition_trend = Column(String(30))
    earlier_defect_count = Column(Integer, default=0)
    later_defect_count = Column(Integer, default=0)
    area_delta_pct = Column(Float, default=0.0)
    side_by_side_path = Column(String(300), nullable=True)
    summary_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==============================================================================
# 10. ROUTE RECOMMENDATION & NAVIGATION AUDIT LOG
# ==============================================================================
class RouteRecommendationLog(Base):
    __tablename__ = "route_recommendation_logs"
    id = Column(Integer, primary_key=True, index=True)
    origin_name = Column(String(150))
    origin_lat = Column(Float)
    origin_lon = Column(Float)
    destination_name = Column(String(150))
    destination_lat = Column(Float)
    destination_lon = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    recommended_route_id = Column(Integer)
    route_summary_json = Column(Text) # JSON string of alternatives, exposure scores, safety advice
