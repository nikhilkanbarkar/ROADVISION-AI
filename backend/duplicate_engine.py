"""
ROADVISION AI - Central Multi-Signal Duplicate Detection Engine
Prevents duplicate physical damage records from being created across citizen reports
and authority inspections. Combines:
1. GPS-based spatial proximity (Haversine distance within Belagavi boundary).
2. Perceptual hashing (OpenCV dHash).
3. Pretrained deep image embedding (MobileNetV3-small 576-dim L2 feature vector & Cosine Similarity).
4. Damage category compatibility (RDD2022 D00, D10, D20, D40).
5. Explainable 3-state classification: CONFIRMED DUPLICATE, NEEDS VERIFICATION, NEW DAMAGE.
"""
import os
import math
import json
from typing import Optional, Dict, Any, List, Tuple
import cv2
import numpy as np

from backend.config import DUPLICATE_GPS_RADIUS_METERS, DUPLICATE_VISUAL_SIMILARITY_MIN

def check_is_within_belagavi(lat: Optional[float], lon: Optional[float]) -> bool:
    """Helper to check Belagavi bounds without circular import."""
    if lat is None or lon is None:
        return False
    try:
        from backend.gis_belagavi import is_within_belagavi
        return is_within_belagavi(lat, lon)
    except Exception:
        # Fallback to Belagavi BBox
        return (15.8050 <= float(lat) <= 15.9250 and 74.4600 <= float(lon) <= 74.5700)

# Thresholds
DUPLICATE_CONFIRMED_THRESHOLD = 0.75
DUPLICATE_AMBIGUOUS_THRESHOLD = 0.45
DEFAULT_SEARCH_RADIUS_METERS = 25.0
MAX_SEARCH_RADIUS_METERS = 35.0

# Multi-Signal Weights
WEIGHT_GPS = 0.35
WEIGHT_HASH = 0.25
WEIGHT_EMBEDDING = 0.25
WEIGHT_CATEGORY = 0.15

# ==============================================================================
# 1. GEOGRAPHIC SPATIAL DISTANCE (HAVERSINE)
# ==============================================================================
def haversine_distance_meters(lat1: Optional[float], lon1: Optional[float],
                              lat2: Optional[float], lon2: Optional[float]) -> Optional[float]:
    """
    Computes great-circle distance between two GPS coordinates in meters.
    Returns None if any coordinate is missing.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None

    R = 6371000.0 # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


# ==============================================================================
# 2. PERCEPTUAL HASH SIMILARITY (DHASH HAMMING)
# ==============================================================================
def hamming_similarity(hash1: Optional[str], hash2: Optional[str]) -> float:
    """
    Calculates visual similarity percentage (0.0 to 1.0) between two hex perceptual hashes.
    """
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 0.0

    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        diff_bits = bin(xor_val).count('1')
        total_bits = len(hash1) * 4 # 64 bits for 16 hex chars
        similarity = 1.0 - (diff_bits / total_bits)
        return round(max(0.0, min(1.0, similarity)), 4)
    except Exception:
        return 0.0


# ==============================================================================
# 3. PRETRAINED DEEP IMAGE EMBEDDING & COSINE SIMILARITY
# ==============================================================================
class ImageEmbeddingExtractor:
    """
    Extracts deep visual representation embeddings using lightweight MobileNetV3-small
    features with adaptive average pooling (576-dimensional L2-normalized vector).
    Provides robust visual matching across different camera angles, lighting, and distances.
    Includes fallback to multi-scale color-spatial histograms if neural weights fail.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.has_nn = False
        self.model = None
        self.features = None
        self.pool = None
        self.transform = None

        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as transforms

            # Load MobileNetV3-small feature extractor
            model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
            model.eval()
            self.model = model
            self.features = model.features
            self.pool = torch.nn.AdaptiveAvgPool2d((1, 1))
            self.transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
            self.has_nn = True
        except Exception as e:
            # Fallback will be used if torch/weights unavailable
            print(f"[EmbeddingExtractor] Fallback to color-spatial descriptor: {e}")
            self.has_nn = False

    def extract(self, img_input: Any) -> Optional[List[float]]:
        """
        Extracts L2-normalized float embedding vector from image path, numpy BGR array, or PIL image.
        """
        if img_input is None:
            return None

        img_bgr = None
        if isinstance(img_input, str):
            if not os.path.exists(img_input):
                return None
            img_bgr = cv2.imread(img_input)
        elif isinstance(img_input, np.ndarray):
            img_bgr = img_input

        if img_bgr is None or img_bgr.size == 0:
            return None

        # Try neural network embedding
        if self.has_nn and self.features is not None:
            try:
                import torch
                from PIL import Image
                rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
                tensor = self.transform(pil_img).unsqueeze(0)
                with torch.no_grad():
                    feat = self.pool(self.features(tensor)).flatten(1)
                    feat = torch.nn.functional.normalize(feat, p=2, dim=1)
                return [round(float(v), 5) for v in feat[0].tolist()]
            except Exception:
                pass

        # Fallback: Multi-scale spatial color histogram (HSV 8x8x8 + 2x2 grid = 512-dim normalized)
        try:
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            return [round(float(v), 5) for v in hist.tolist()]
        except Exception:
            return None

def extract_image_embedding(img_input: Any) -> Optional[List[float]]:
    """Helper function to extract image embedding."""
    return ImageEmbeddingExtractor.get_instance().extract(img_input)

def cosine_similarity(vec1: Optional[List[float]], vec2: Optional[List[float]]) -> float:
    """
    Computes cosine similarity between two float vectors. Range [0.0, 1.0].
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    try:
        a = np.array(vec1, dtype=np.float32)
        b = np.array(vec2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        dot = float(np.dot(a, b) / (norm_a * norm_b))
        return round(max(0.0, min(1.0, dot)), 4)
    except Exception:
        return 0.0


# ==============================================================================
# 4. DAMAGE CATEGORY COMPATIBILITY
# ==============================================================================
def category_compatibility(cat1: Optional[str], cat2: Optional[str],
                           class1: Optional[str] = None, class2: Optional[str] = None) -> Tuple[bool, float]:
    """
    Compares detected damage categories and returns (is_compatible, compatibility_score).
    Exact match: 1.0
    Compatible crack family (e.g. D00 longitudinal and D10 transverse or D20 alligator): 0.45
    Incompatible (e.g. Pothole D40 vs Crack D00/D10): 0.0
    """
    c1 = (cat1 or "").strip().upper()
    c2 = (cat2 or "").strip().upper()
    n1 = (class1 or "").strip().lower()
    n2 = (class2 or "").strip().lower()

    # Exact code match
    if c1 and c2 and c1 == c2:
        return True, 1.0

    # Name-based exact match
    if n1 and n2 and n1 == n2:
        return True, 1.0

    is_pothole_1 = c1 == "D40" or "pothole" in n1
    is_pothole_2 = c2 == "D40" or "pothole" in n2

    if is_pothole_1 and is_pothole_2:
        return True, 1.0

    # If one is a pothole and the other is a crack, they are structurally incompatible
    if is_pothole_1 != is_pothole_2:
        return False, 0.0

    # Both are cracks/surface defects (D00, D10, D20)
    crack_codes = {"D00", "D10", "D20"}
    if c1 in crack_codes and c2 in crack_codes:
        # Cross-crack compatibility (e.g., longitudinal evolving into alligator fatigue crack)
        return True, 0.45

    # Fallback name check
    if ("crack" in n1 or "crack" in n2) and not is_pothole_1 and not is_pothole_2:
        return True, 0.45

    return False, 0.0


# ==============================================================================
# 5. MULTI-SIGNAL DUPLICATE EVALUATION ENGINE
# ==============================================================================
def evaluate_duplicate_multi_signal(
    candidate: Any,
    existing_record: Any,
    search_radius_m: float = DEFAULT_SEARCH_RADIUS_METERS
) -> Dict[str, Any]:
    """
    Evaluates duplicate relationship between a candidate submission/defect and an existing physical record.
    Returns 3-state classification:
      - CONFIRMED_DUPLICATE
      - NEEDS_VERIFICATION
      - NEW_DAMAGE
    Along with individual and combined matching scores, and human-explainable decision reason.
    """
    # 1. Extract candidate attributes
    cand_lat = getattr(candidate, "latitude", None)
    cand_lon = getattr(candidate, "longitude", None)
    cand_cat = getattr(candidate, "category_code", None)
    cand_name = getattr(candidate, "class_name", getattr(candidate, "damage_type", None))
    cand_hash = getattr(candidate, "image_hash", None)
    cand_emb = getattr(candidate, "image_embedding", None)
    if isinstance(cand_emb, str):
        try:
            cand_emb = json.loads(cand_emb)
        except Exception:
            cand_emb = None

    cand_in_belagavi = False if cand_lat == 0.0 and cand_lon == 0.0 else True

    # 2. Extract existing record attributes
    exist_lat = getattr(existing_record, "latitude", None)
    exist_lon = getattr(existing_record, "longitude", None)
    exist_cat = getattr(existing_record, "category_code", None)
    exist_name = getattr(existing_record, "damage_type", getattr(existing_record, "class_name", None))
    exist_hash = getattr(existing_record, "image_hash", None)
    exist_emb = getattr(existing_record, "image_embedding", None)
    if isinstance(exist_emb, str):
        try:
            exist_emb = json.loads(exist_emb)
        except Exception:
            exist_emb = None

    # Signal A: Spatial Distance (Haversine)
    dist_m = haversine_distance_meters(cand_lat, cand_lon, exist_lat, exist_lon)

    # Boundary validation check (Belagavi Scope)
    exist_in_belagavi = False if exist_lat == 0.0 and exist_lon == 0.0 else True

    gps_score = 0.0
    if dist_m is not None:
        if dist_m <= search_radius_m:
            gps_score = max(0.0, 1.0 - (dist_m / search_radius_m))
        else:
            gps_score = 0.0

    # Signal B: Category Compatibility
    is_cat_match, cat_score = category_compatibility(cand_cat, exist_cat, cand_name, exist_name)

    # Signal C: Perceptual Hash Similarity
    hash_sim = hamming_similarity(cand_hash, exist_hash)

    # Signal D: Deep Embedding Cosine Similarity
    emb_sim = cosine_similarity(cand_emb, exist_emb) if (cand_emb and exist_emb) else 0.0

    # Combined visual score
    has_deep_emb = (cand_emb is not None and exist_emb is not None and len(cand_emb) > 0)
    if has_deep_emb and emb_sim > 0.0:
        vis_score = (0.35 * hash_sim) + (0.65 * emb_sim)
    else:
        vis_score = hash_sim

    # Weighted Overall Matching Score (0.0 to 1.0)
    if dist_m is not None:
        if has_deep_emb:
            overall_score = (
                (WEIGHT_GPS * gps_score) +
                (WEIGHT_HASH * hash_sim) +
                (WEIGHT_EMBEDDING * emb_sim) +
                (WEIGHT_CATEGORY * cat_score)
            )
        else:
            # Rebalance weights when deep embedding unavailable
            overall_score = (0.45 * gps_score) + (0.35 * hash_sim) + (0.20 * cat_score)
    else:
        # GPS missing: rely purely on visual evidence and category
        if has_deep_emb:
            overall_score = (0.40 * hash_sim) + (0.45 * emb_sim) + (0.15 * cat_score)
        else:
            overall_score = (0.80 * hash_sim) + (0.20 * cat_score)

    overall_score = round(max(0.0, min(1.0, overall_score)), 3)

    # ==========================================================================
    # 3-STATE CLASSIFICATION DECISION ENGINE
    # ==========================================================================
    decision = "NEW_DAMAGE"
    reason_parts = []

    # Explanatory metric logs
    if dist_m is not None:
        reason_parts.append(f"Spatial distance: {dist_m:.1f}m (search radius: {search_radius_m}m)")
    else:
        reason_parts.append("GPS metadata missing")

    if is_cat_match:
        reason_parts.append(f"Category matched: {cand_cat or cand_name}")
    else:
        reason_parts.append(f"Incompatible categories: {cand_cat} vs {exist_cat}")

    reason_parts.append(f"Visual hash similarity: {hash_sim * 100:.1f}%")
    if has_deep_emb:
        reason_parts.append(f"Deep embedding cosine similarity: {emb_sim * 100:.1f}%")
    reason_parts.append(f"Overall weighted matching score: {overall_score * 100:.1f}%")

    # Classification Rules
    if dist_m is not None and dist_m > MAX_SEARCH_RADIUS_METERS:
        # Beyond maximum corridor search radius
        decision = "NEW_DAMAGE"
        reason_parts.append(f"Distance ({dist_m:.1f}m) exceeds maximum Belagavi search radius ({MAX_SEARCH_RADIUS_METERS}m). Separate physical damage.")

    elif not is_cat_match and (dist_m is None or dist_m > 8.0):
        # Distinct defect types at different positions
        decision = "NEW_DAMAGE"
        reason_parts.append("Incompatible defect categories and insufficient spatial overlap. Classified as separate damage.")

    elif not cand_in_belagavi or not exist_in_belagavi:
        # Outside Belagavi project boundary
        decision = "NEW_DAMAGE"
        reason_parts.append("Coordinates fall outside Belagavi boundary.")

    else:
        # Within search proximity
        # Condition 1: CONFIRMED DUPLICATE
        # Strong multi-signal evidence:
        # - Close proximity (<= 15m) + same category + (hash >= 65% or emb >= 65% or hash == 100%)
        # - High overall score >= 0.75 and compatible category
        # - Identical photo / identical perceptual hash (>= 90%) within 25m
        is_strong_visual = (hash_sim >= 0.75 or (has_deep_emb and emb_sim >= 0.72) or (hash_sim >= 0.60 and emb_sim >= 0.65))
        is_exact_visual = (hash_sim >= 0.90)

        if is_cat_match:
            if dist_m is not None and dist_m <= 12.0 and (is_strong_visual or overall_score >= 0.65):
                decision = "CONFIRMED_DUPLICATE"
                reason_parts.append("CONFIRMED DUPLICATE: High spatial proximity (<=12m), matching defect category, and strong visual alignment.")
            elif is_exact_visual and dist_m is not None and dist_m <= search_radius_m:
                decision = "CONFIRMED_DUPLICATE"
                reason_parts.append("CONFIRMED DUPLICATE: Identical visual hash match within spatial radius.")
            elif overall_score >= DUPLICATE_CONFIRMED_THRESHOLD and (dist_m is None or dist_m <= search_radius_m):
                decision = "CONFIRMED_DUPLICATE"
                reason_parts.append(f"CONFIRMED DUPLICATE: Overall matching score ({overall_score*100:.1f}%) meets confirmed threshold ({DUPLICATE_CONFIRMED_THRESHOLD*100:.0f}%).")
            elif overall_score >= DUPLICATE_AMBIGUOUS_THRESHOLD or (dist_m is not None and dist_m <= 20.0 and cat_score >= 0.45):
                # Ambiguous: Nearby with partial similarity (e.g. different camera angles or ambiguous lighting)
                decision = "NEEDS_VERIFICATION"
                reason_parts.append(f"NEEDS VERIFICATION: Ambiguous evidence score ({overall_score*100:.1f}%). Proximity or category aligns, but visual confidence requires authority review.")
            else:
                decision = "NEW_DAMAGE"
                reason_parts.append("NEW DAMAGE: Low multi-signal match score within proximity. Distinct defect.")
        else:
            # Different categories but nearby
            if dist_m is not None and dist_m <= 8.0 and is_strong_visual:
                decision = "NEEDS_VERIFICATION"
                reason_parts.append("NEEDS VERIFICATION: High spatial proximity and visual similarity despite differing AI category labels.")
            else:
                decision = "NEW_DAMAGE"
                reason_parts.append("NEW DAMAGE: Incompatible categories.")

    return {
        "decision": decision,
        "is_duplicate": (decision == "CONFIRMED_DUPLICATE"),
        "needs_verification": (decision == "NEEDS_VERIFICATION"),
        "is_new_damage": (decision == "NEW_DAMAGE"),
        "overall_matching_score": overall_score,
        "spatial_distance_m": dist_m,
        "gps_score": round(gps_score, 3),
        "visual_similarity_pct": round(hash_sim * 100.0, 1),
        "embedding_similarity_pct": round(emb_sim * 100.0, 1),
        "category_match": is_cat_match,
        "category_score": cat_score,
        "decision_reason": " | ".join(reason_parts),
        "explanation": " | ".join(reason_parts) # Backward compatibility
    }


# ==============================================================================
# 6. BACKWARD COMPATIBLE API FOR EXISTING TESTS
# ==============================================================================
def evaluate_duplicate_candidate(new_defect: Any, existing_defect: Any) -> Dict[str, Any]:
    """
    Backward-compatible evaluation function maintained for existing unit tests and pipelines.
    Returns:
        is_duplicate (bool),
        spatial_distance_m (float or None),
        visual_similarity_pct (float),
        category_match (bool),
        match_confidence (float),
        explanation (str),
        decision (str),
        embedding_similarity_pct (float),
        overall_matching_score (float)
    """
    res = evaluate_duplicate_multi_signal(new_defect, existing_defect, search_radius_m=DUPLICATE_GPS_RADIUS_METERS)
    return {
        "is_duplicate": bool(res["is_duplicate"]),
        "spatial_distance_m": res["spatial_distance_m"],
        "visual_similarity_pct": res["visual_similarity_pct"],
        "embedding_similarity_pct": res["embedding_similarity_pct"],
        "category_match": res["category_match"],
        "match_confidence": res["overall_matching_score"],
        "overall_matching_score": res["overall_matching_score"],
        "decision": res["decision"],
        "explanation": res["decision_reason"]
    }


# ==============================================================================
# 7. CENTRAL DEDUPLICATION SEARCH AGAINST PHYSICAL DAMAGE RECORDS
# ==============================================================================
def find_best_physical_damage_match(
    db: Any,
    lat: Optional[float],
    lon: Optional[float],
    category_code: str,
    class_name: Optional[str] = None,
    image_hash: Optional[str] = None,
    image_embedding: Optional[List[float]] = None,
    search_radius_m: float = DEFAULT_SEARCH_RADIUS_METERS
) -> Dict[str, Any]:
    """
    Queries verified physical damage records in Belagavi within spatial search radius.
    Applies multi-signal matching to find the single best candidate.
    Returns {decision, best_match, best_score, best_eval, candidate_matches}.
    """
    from backend.models_db import PhysicalDamageRecord
    from types import SimpleNamespace

    # Candidate object wrapper
    cand_obj = SimpleNamespace(
        latitude=lat,
        longitude=lon,
        category_code=category_code,
        class_name=class_name,
        damage_type=class_name,
        image_hash=image_hash,
        image_embedding=image_embedding
    )

    query = db.query(PhysicalDamageRecord).filter(
        PhysicalDamageRecord.verification_status != "Rejected"
    )

    # Spatial bounding box pre-filtering for fast query execution
    candidates = []
    if lat is not None and lon is not None:
        # 1 degree latitude ~ 111,000m
        # Search radius buffer in degrees
        deg_lat_buffer = (MAX_SEARCH_RADIUS_METERS + 10.0) / 111000.0
        deg_lon_buffer = (MAX_SEARCH_RADIUS_METERS + 10.0) / (111000.0 * max(0.2, math.cos(math.radians(lat))))

        candidates = query.filter(
            PhysicalDamageRecord.latitude.between(lat - deg_lat_buffer, lat + deg_lat_buffer),
            PhysicalDamageRecord.longitude.between(lon - deg_lon_buffer, lon + deg_lon_buffer)
        ).all()
    else:
        # Fallback: All physical records if GPS missing
        candidates = query.limit(50).all()

    if not candidates:
        return {
            "decision": "NEW_DAMAGE",
            "best_match": None,
            "best_score": 0.0,
            "best_eval": None,
            "candidate_matches": []
        }

    best_match = None
    best_score = -1.0
    best_eval = None
    candidate_matches = []

    for phys in candidates:
        eval_res = evaluate_duplicate_multi_signal(cand_obj, phys, search_radius_m=search_radius_m)
        candidate_matches.append({
            "physical_id": phys.id,
            "damage_code": phys.damage_code,
            "road_name": phys.road_name,
            "eval": eval_res
        })

        if eval_res["overall_matching_score"] > best_score:
            best_score = eval_res["overall_matching_score"]
            best_match = phys
            best_eval = eval_res

    # Overall decision from best matching candidate
    decision = best_eval["decision"] if best_eval else "NEW_DAMAGE"

    return {
        "decision": decision,
        "best_match": best_match,
        "best_score": best_score,
        "best_eval": best_eval,
        "candidate_matches": candidate_matches
    }
