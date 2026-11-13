"""
ROADVISION AI - Test Suite for Cross-Inspection Duplicate Detection Engine
Tests spatial proximity, perceptual hash similarity, and candidate flagging.
"""
from types import SimpleNamespace
from backend.duplicate_engine import haversine_distance_meters, hamming_similarity, evaluate_duplicate_candidate

def test_haversine_distance():
    # Delhi Connaught Place to India Gate ~ 2.4 km
    lat1, lon1 = 28.6315, 77.2167
    lat2, lon2 = 28.6129, 77.2295
    dist = haversine_distance_meters(lat1, lon1, lat2, lon2)
    assert 2300 < dist < 2600

    # Same location
    assert haversine_distance_meters(lat1, lon1, lat1, lon1) == 0.0

    # Missing coordinates
    assert haversine_distance_meters(None, None, lat1, lon1) is None

def test_hamming_similarity():
    h1 = "ffff0000ffff0000"
    h2 = "ffff0000ffff0000"
    assert hamming_similarity(h1, h2) == 1.0

    # 1 bit difference
    h3 = "ffff0000ffff0001"
    sim = hamming_similarity(h1, h3)
    assert sim >= 0.98

    # Completely different
    h4 = "0000ffff0000ffff"
    assert hamming_similarity(h1, h4) == 0.0

def test_duplicate_candidate_evaluation_same_location():
    # Two reports 8 meters apart with same category and high visual similarity
    d1 = SimpleNamespace(
        id=1, category_code="D40", class_name="pothole",
        latitude=28.4595, longitude=77.0266, image_hash="a1b2c3d4e5f60718"
    )
    d2 = SimpleNamespace(
        id=2, category_code="D40", class_name="pothole",
        latitude=28.45957, longitude=77.02665, image_hash="a1b2c3d4e5f60718"
    )

    res = evaluate_duplicate_candidate(d2, d1)
    assert res["is_duplicate"] is True
    assert res["spatial_distance_m"] < 15.0
    assert res["visual_similarity_pct"] == 100.0

def test_duplicate_candidate_different_locations():
    d1 = SimpleNamespace(
        id=1, category_code="D40", class_name="pothole",
        latitude=28.4595, longitude=77.0266, image_hash="a1b2c3d4e5f60718"
    )
    # 5 km away
    d2 = SimpleNamespace(
        id=2, category_code="D40", class_name="pothole",
        latitude=28.5000, longitude=77.0800, image_hash="ffffffffffffffff"
    )
    res = evaluate_duplicate_candidate(d2, d1)
    assert res["is_duplicate"] is False
    assert res["spatial_distance_m"] > 1000.0
