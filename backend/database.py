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
from datetime import datetime
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
                if "osm_names" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN osm_names TEXT"))
                if "geometry_source" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN geometry_source VARCHAR(100) DEFAULT 'OSRM/OpenStreetMap'"))
                if "geometry_updated_at" not in rs_cols:
                    conn.execute(text("ALTER TABLE road_segments ADD COLUMN geometry_updated_at DATETIME"))
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

def seed_road_conditions():
    """Synchronize stored road geometry from the bundled OSM-derived corridor catalog."""
    from backend.models_db import RoadSegment
    from backend.gis_belagavi import BELAGAVI_ROAD_SEGMENTS
    db = SessionLocal()
    try:
        for road in BELAGAVI_ROAD_SEGMENTS:
            segment = db.query(RoadSegment).filter(
                RoadSegment.segment_code == road["code"]
            ).first()
            if segment is None:
                segment = db.query(RoadSegment).filter(RoadSegment.id == road["id"]).first()
            if segment is None:
                segment = RoadSegment(
                    id=road["id"],
                    segment_code=road["code"],
                    name=road["name"],
                    location="Belagavi, Karnataka",
                    potholes_count=0,
                    total_damage_count=0,
                    condition_percentage=100.0,
                    risk_classification="SAFE",
                    inspection_source="OSM geometry only",
                    verification_status="UNINSPECTED"
                )
                db.add(segment)

            coordinates = road["coordinates"]
            start = coordinates[0]
            end = coordinates[-1]
            segment.segment_code = road["code"]
            segment.name = road["name"]
            segment.road_type = road.get("road_type") or "Road"
            segment.speed_limit = road.get("speed_limit") or 50
            segment.from_node = None
            segment.to_node = None
            segment.start_lat = start[1]
            segment.start_lon = start[0]
            segment.end_lat = end[1]
            segment.end_lon = end[0]
            segment.length_m = road["length_m"]
            segment.geometry_geojson = json.dumps(coordinates, separators=(",", ":"))
            segment.osm_names = json.dumps(road.get("osm_names") or [], separators=(",", ":"))
            segment.geometry_source = road["geometry_source"]
            updated_at = road.get("geometry_updated_at")
            if updated_at:
                segment.geometry_updated_at = datetime.fromisoformat(
                    updated_at.replace("Z", "+00:00")
                ).replace(tzinfo=None)
            segment.surface_type = road.get("surface") or "Unknown"
            if segment.inspection_source in (None, "Demonstration Sample"):
                segment.potholes_count = 0
                segment.total_damage_count = 0
                segment.condition_percentage = 100.0
                segment.risk_classification = "SAFE"
                segment.inspection_source = "OSM geometry only"
                segment.verification_status = "UNINSPECTED"
        db.commit()
        print(f"[Database] Synchronized {len(BELAGAVI_ROAD_SEGMENTS)} OSM road geometries.")
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Unable to synchronize OSM road geometries: {exc}") from exc
    finally:
        db.close()

def init_db():
    from backend import models_db
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    seed_road_conditions()
    print("Database tables initialized and synchronized successfully.")
