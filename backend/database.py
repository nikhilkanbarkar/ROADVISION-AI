"""
ROADVISION AI - Database Connection and Initialization
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
ROADVISION AI - Database Connection, Schema Migration and Initialization
"""
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_schema():
    """Safely adds missing columns to existing SQLite tables without losing data."""
    with engine.connect() as conn:
        # Check road_segments columns
        try:
            rs_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(road_segments)")).fetchall()]
            if rs_cols:
                if "location" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN location VARCHAR(200) DEFAULT 'Belagavi, Karnataka'"))
                if "potholes_count" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN potholes_count INTEGER DEFAULT 0"))
                if "total_damage_count" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN total_damage_count INTEGER DEFAULT 0"))
                if "condition_percentage" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN condition_percentage FLOAT DEFAULT 95.0"))
                if "risk_classification" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN risk_classification VARCHAR(20) DEFAULT 'SAFE'"))
                if "inspection_source" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN inspection_source VARCHAR(50) DEFAULT 'Demonstration Sample'"))
                if "verification_status" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN verification_status VARCHAR(30) DEFAULT 'VERIFIED'"))
        except Exception as e:
            print(f"[Migration] road_segments note: {e}")

        # Check submissions columns
        try:
            sub_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(submissions)")).fetchall()]
            if sub_cols:
                if "potholes_count" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN potholes_count INTEGER DEFAULT 0"))
                if "condition_percentage" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN condition_percentage FLOAT DEFAULT 100.0"))
                if "risk_classification" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN risk_classification VARCHAR(20) DEFAULT 'SAFE'"))
                if "road_segment_id" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN road_segment_id INTEGER"))
                if "verified_by" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN verified_by VARCHAR(100)"))
                if "verified_at" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN verified_at DATETIME"))
                if "verification_notes" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN verification_notes TEXT"))
                if "physical_damage_id" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN physical_damage_id INTEGER"))
                if "duplicate_status" not in sub_cols:
                    conn.execute(text("ALTER TABLE submissions ADD COLUMN duplicate_status VARCHAR(35) DEFAULT 'Unique'"))
        except Exception as e:
            print(f"[Migration] submissions note: {e}")

        # Check duplicate_matches columns
        try:
            dm_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(duplicate_matches)")).fetchall()]
            if dm_cols:
                if "embedding_similarity_pct" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN embedding_similarity_pct FLOAT DEFAULT 0.0"))
                if "overall_matching_score" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN overall_matching_score FLOAT DEFAULT 0.0"))
                if "decision_status" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN decision_status VARCHAR(35) DEFAULT 'Needs_Verification'"))
                if "decision_reason" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN decision_reason TEXT"))
                if "candidate_photo_path" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN candidate_photo_path VARCHAR(300)"))
                if "existing_photo_path" not in dm_cols:
                    conn.execute(text("ALTER TABLE duplicate_matches ADD COLUMN existing_photo_path VARCHAR(300)"))
        except Exception as e:
            print(f"[Migration] duplicate_matches note: {e}")

        # Check physical_damage_records columns
        try:
            pdr_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(physical_damage_records)")).fetchall()]
            if pdr_cols:
                if "image_embedding" not in pdr_cols:
                    conn.execute(text("ALTER TABLE physical_damage_records ADD COLUMN image_embedding TEXT"))
        except Exception as e:
            print(f"[Migration] physical_damage_records note: {e}")

        # Check ai_detections columns
        try:
            ai_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(ai_detections)")).fetchall()]
            if ai_cols:
                if "image_embedding" not in ai_cols:
                    conn.execute(text("ALTER TABLE ai_detections ADD COLUMN image_embedding TEXT"))
        except Exception as e:
            print(f"[Migration] ai_detections note: {e}")

        conn.commit()

# Curated demonstration baseline profiles for Belagavi road network
BELAGAVI_ROAD_CONDITIONS = {
    1: {"potholes": 5, "damage": 8, "condition": 38.5, "risk": "RISKY", "loc": "Tilakwadi, Belagavi"},
    2: {"potholes": 2, "damage": 4, "condition": 68.0, "risk": "MODERATE", "loc": "Udyambag, Belagavi"},
    3: {"potholes": 2, "damage": 4, "condition": 72.0, "risk": "MODERATE", "loc": "Camp / Tilakwadi, Belagavi"},
    4: {"potholes": 1, "damage": 3, "condition": 74.5, "risk": "MODERATE", "loc": "Bogarves, Belagavi"},
    5: {"potholes": 0, "damage": 1, "condition": 88.5, "risk": "SAFE", "loc": "Hindwadi, Belagavi"},
    6: {"potholes": 0, "damage": 1, "condition": 91.0, "risk": "SAFE", "loc": "Civil Hospital, Belagavi"},
    7: {"potholes": 0, "damage": 0, "condition": 95.0, "risk": "SAFE", "loc": "Camp Cantonment, Belagavi"},
    8: {"potholes": 4, "damage": 5, "condition": 48.0, "risk": "RISKY", "loc": "Camp, Belagavi"},
    9: {"potholes": 0, "damage": 0, "condition": 98.0, "risk": "SAFE", "loc": "Kanbargi / NH-48, Belagavi"},
    10: {"potholes": 0, "damage": 1, "condition": 94.0, "risk": "SAFE", "loc": "Auto Nagar / NH-48, Belagavi"},
    11: {"potholes": 0, "damage": 0, "condition": 96.5, "risk": "SAFE", "loc": "Halaga / Suvarna Soudha, Belagavi"},
    12: {"potholes": 0, "damage": 1, "condition": 89.0, "risk": "SAFE", "loc": "Fort Lake, Belagavi"},
    13: {"potholes": 6, "damage": 9, "condition": 34.0, "risk": "RISKY", "loc": "Shahapur, Belagavi"},
    14: {"potholes": 2, "damage": 4, "condition": 66.5, "risk": "MODERATE", "loc": "Shahapur / Vadgaon, Belagavi"},
    15: {"potholes": 3, "damage": 5, "condition": 62.0, "risk": "MODERATE", "loc": "Vadgaon, Belagavi"},
    16: {"potholes": 2, "damage": 3, "condition": 70.0, "risk": "MODERATE", "loc": "Central Belagavi"},
    17: {"potholes": 2, "damage": 4, "condition": 67.5, "risk": "MODERATE", "loc": "Khade Bazar, Belagavi"},
    18: {"potholes": 2, "damage": 3, "condition": 72.0, "risk": "MODERATE", "loc": "Tilakwadi, Belagavi"},
    19: {"potholes": 0, "damage": 0, "condition": 93.0, "risk": "SAFE", "loc": "RPD Cross, Belagavi"},
    20: {"potholes": 0, "damage": 1, "condition": 87.0, "risk": "SAFE", "loc": "RPD / Udyambag, Belagavi"},
    21: {"potholes": 4, "damage": 6, "condition": 46.0, "risk": "RISKY", "loc": "SPM Road, Belagavi"},
    22: {"potholes": 0, "damage": 0, "condition": 94.5, "risk": "SAFE", "loc": "Kanbargi, Belagavi"},
    23: {"potholes": 5, "damage": 7, "condition": 41.0, "risk": "RISKY", "loc": "Halaga, Belagavi"},
    24: {"potholes": 0, "damage": 0, "condition": 97.0, "risk": "SAFE", "loc": "Military Camp, Belagavi"},
    25: {"potholes": 0, "damage": 1, "condition": 89.5, "risk": "SAFE", "loc": "Kakaves, Belagavi"},
    26: {"potholes": 1, "damage": 3, "condition": 76.0, "risk": "MODERATE", "loc": "BIMS / Fort, Belagavi"},
    27: {"potholes": 0, "damage": 0, "condition": 92.0, "risk": "SAFE", "loc": "Nath Pai Circle, Belagavi"},
    28: {"potholes": 4, "damage": 6, "condition": 44.5, "risk": "RISKY", "loc": "Maratha Colony, Belagavi"},
    29: {"potholes": 1, "damage": 2, "condition": 78.0, "risk": "MODERATE", "loc": "Hindwadi, Belagavi"},
    30: {"potholes": 0, "damage": 1, "condition": 88.0, "risk": "SAFE", "loc": "Tilakwadi West, Belagavi"}
}

def seed_road_conditions():
    """Initializes Belagavi road network segments with realistic baseline road condition data."""
    from backend.models_db import RoadSegment, RoadInspectionHistory
    from backend.gis_belagavi import BELAGAVI_ROAD_SEGMENTS
    db = SessionLocal()
    try:
        existing_count = db.query(RoadSegment).count()
        if existing_count == 0:
            for r in BELAGAVI_ROAD_SEGMENTS:
                seg_id = r["id"]
                prof = BELAGAVI_ROAD_CONDITIONS.get(seg_id, {"potholes": 0, "damage": 0, "condition": 95.0, "risk": "SAFE", "loc": "Belagavi"})
                seg = RoadSegment(
                    id=seg_id,
                    segment_code=r["code"],
                    name=r["name"],
                    location=prof["loc"],
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
                    surface_type=r["surface"],
                    potholes_count=prof["potholes"],
                    total_damage_count=prof["damage"],
                    condition_percentage=prof["condition"],
                    risk_classification=prof["risk"],
                    inspection_source="Demonstration Sample",
                    verification_status="VERIFIED",
                    last_inspected_date=datetime.utcnow() - timedelta(days=(seg_id % 7 + 1))
                )
                db.add(seg)
                db.flush()

                # Add initial demonstration inspection history record
                hist = RoadInspectionHistory(
                    road_segment_id=seg.id,
                    inspection_date=seg.last_inspected_date or datetime.utcnow(),
                    potholes_count=prof["potholes"],
                    total_damage_count=prof["damage"],
                    condition_percentage=prof["condition"],
                    risk_classification=prof["risk"],
                    inspection_source="Demonstration Sample",
                    inspector_name="Belagavi PWD Road Health Survey",
                    notes=f"Initial demonstration baseline inspection for {r['name']}."
                )
                db.add(hist)
            db.commit()
            print(f"[Database] Successfully seeded {len(BELAGAVI_ROAD_SEGMENTS)} Belagavi road condition records.")
        else:
            # Update existing segments if condition fields are default or unpopulated
            segments = db.query(RoadSegment).all()
            for s in segments:
                if s.id in BELAGAVI_ROAD_CONDITIONS and (s.potholes_count is None or s.condition_percentage is None or s.condition_percentage == 95.0 and s.potholes_count == 0):
                    prof = BELAGAVI_ROAD_CONDITIONS[s.id]
                    s.potholes_count = prof["potholes"]
                    s.total_damage_count = prof["damage"]
                    s.condition_percentage = prof["condition"]
                    s.risk_classification = prof["risk"]
                    s.location = prof["loc"]
                    if not s.inspection_source:
                        s.inspection_source = "Demonstration Sample"
                    if not s.verification_status:
                        s.verification_status = "VERIFIED"
                    if not s.last_inspected_date:
                        s.last_inspected_date = datetime.utcnow() - timedelta(days=(s.id % 7 + 1))

                    # Check if history exists
                    h_cnt = db.query(RoadInspectionHistory).filter(RoadInspectionHistory.road_segment_id == s.id).count()
                    if h_cnt == 0:
                        hist = RoadInspectionHistory(
                            road_segment_id=s.id,
                            inspection_date=s.last_inspected_date or datetime.utcnow(),
                            potholes_count=prof["potholes"],
                            total_damage_count=prof["damage"],
                            condition_percentage=prof["condition"],
                            risk_classification=prof["risk"],
                            inspection_source="Demonstration Sample",
                            inspector_name="Belagavi PWD Road Health Survey",
                            notes=f"Initial demonstration baseline inspection for {s.name}."
                        )
                        db.add(hist)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Database] Seeding error: {e}")
    finally:
        db.close()

def init_db():
    from backend import models_db
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    seed_road_conditions()
    print("Database tables initialized and synchronized successfully.")
