"""
ROADVISION AI - Cross-Inspection Duplicate Detection Engine
Calculates spatial proximity via Haversine distance, visual similarity via perceptual
hash Hamming distance, and generates explainable duplicate match candidates.
"""
import math
from backend.config import DUPLICATE_GPS_RADIUS_METERS, DUPLICATE_VISUAL_SIMILARITY_MIN

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """
    Computes great-circle distance between two GPS coordinates in meters.
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

def hamming_similarity(hash1, hash2):
    """
    Calculates visual similarity percentage (0.0 to 1.0) between two hex perceptual hashes.
    """
    if not hash1 or not hash2 or len(hash1) != len(hash2):
        return 0.0

    try:
        val1 = int(hash1, 16)
        val2 = int(hash2, 16)
        xor_val = val1 ^ val2
        # Count set bits
        diff_bits = bin(xor_val).count('1')
        total_bits = len(hash1) * 4 # 64 bits for 16 hex chars
        similarity = 1.0 - (diff_bits / total_bits)
        return round(max(0.0, min(1.0, similarity)), 4)
    except Exception:
        return 0.0

def evaluate_duplicate_candidate(new_defect, existing_defect):
    """
    Evaluates whether two defect records represent the same physical road defect.
    Returns:
        is_candidate (bool),
        spatial_distance_m (float or None),
        visual_similarity (float),
        category_match (bool),
        confidence_score (float),
        reason (str)
    """
    # 1. Category match
    cat_match = (
        new_defect.category_code == existing_defect.category_code or
        new_defect.class_name == existing_defect.class_name
    )

    # 2. Spatial distance
    dist_m = haversine_distance_meters(
        new_defect.latitude, new_defect.longitude,
        existing_defect.latitude, existing_defect.longitude
    )

    # 3. Visual similarity
    vis_sim = hamming_similarity(new_defect.image_hash, existing_defect.image_hash)

    # Decision logic
    is_duplicate = False
    confidence = 0.0
    reason_parts = []

    if dist_m is not None:
        if dist_m <= DUPLICATE_GPS_RADIUS_METERS:
            # Within 25m radius
            spatial_score = max(0.0, 1.0 - (dist_m / DUPLICATE_GPS_RADIUS_METERS))
            confidence = (spatial_score * 0.55) + (vis_sim * 0.30) + (0.15 if cat_match else 0.0)
            reason_parts.append(f"Located {dist_m:.1f}m away (threshold: {DUPLICATE_GPS_RADIUS_METERS}m)")

            if cat_match and (dist_m <= 15.0 or vis_sim >= 0.65):
                is_duplicate = True
            elif vis_sim >= DUPLICATE_VISUAL_SIMILARITY_MIN:
                is_duplicate = True
        else:
            reason_parts.append(f"Different location ({dist_m:.1f}m apart)")
    else:
        # GPS missing: rely strictly on high visual similarity + category match
        if cat_match and vis_sim >= DUPLICATE_VISUAL_SIMILARITY_MIN:
            is_duplicate = True
            confidence = vis_sim
            reason_parts.append(f"Visual similarity match {vis_sim*100:.1f}% (No GPS metadata)")
        else:
            reason_parts.append(f"Insufficient visual match ({vis_sim*100:.1f}%) and missing GPS")

    if cat_match:
        reason_parts.append(f"Matching category: {new_defect.category_code}")
    else:
        reason_parts.append(f"Different categories: {new_defect.category_code} vs {existing_defect.category_code}")

    if vis_sim > 0.0:
        reason_parts.append(f"Visual hash similarity: {vis_sim*100:.1f}%")

    return {
        "is_duplicate": is_duplicate,
        "spatial_distance_m": dist_m,
        "visual_similarity_pct": round(vis_sim * 100, 1),
        "category_match": cat_match,
        "match_confidence": round(confidence, 3),
        "explanation": " | ".join(reason_parts)
    }
