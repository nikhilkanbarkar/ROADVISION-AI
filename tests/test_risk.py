"""
ROADVISION AI - Test Suite for Road Risk Assessment Engine
Tests normalized 0-100 scoring, contributing factors, and risk tier categorization.
"""
from backend.risk_engine import calculate_road_risk_score
from backend.risk_engine import compute_road_condition

def test_empty_defects_zero_risk():
    score, tier, breakdown = calculate_road_risk_score([])
    assert score == 0.0
    assert tier == "Low"
    assert len(breakdown["contributing_factors"]) > 0

def test_critical_risk_highway_severe_potholes():
    severe_defects = [
        {"category_code": "D40", "severity": "Severe"},
        {"category_code": "D40", "severity": "Severe"},
        {"category_code": "D20", "severity": "Moderate"}
    ]
    score, tier, breakdown = calculate_road_risk_score(
        defects=severe_defects,
        road_type="Highway",
        speed_limit=90,
        traffic_volume="High",
        weather_condition="Rainy/Wet"
    )
    assert score >= 75.0
    assert tier == "Critical"
    assert breakdown["defect_counts"]["D40"] == 2
    assert breakdown["severity_counts"]["Severe"] == 2
    assert any("pothole" in r.lower() for r in breakdown["contributing_factors"])

def test_minor_crack_residential_low_risk():
    minor_defects = [
        {"category_code": "D00", "severity": "Minor"}
    ]
    score, tier, breakdown = calculate_road_risk_score(
        defects=minor_defects,
        road_type="Residential",
        speed_limit=30,
        traffic_volume="Low",
        weather_condition="Clear/Dry"
    )
    assert score <= 30.0
    assert tier in ["Low", "Moderate"]

def test_score_bounded_0_to_100():
    # Massive cluster of defects
    many_defects = [{"category_code": "D40", "severity": "Severe"}] * 50
    score, tier, _ = calculate_road_risk_score(
        defects=many_defects,
        road_type="Highway",
        speed_limit=120,
        traffic_volume="High",
        weather_condition="Rainy/Wet"
    )
    assert 0.0 <= score <= 100.0


def test_single_low_severity_pothole_can_still_be_classified_healthy():
    condition = compute_road_condition(
        potholes_count=1,
        total_damage_count=1,
        minor_count=1,
        speed_limit=40,
        road_type="Local"
    )

    assert condition["condition_percentage"] >= 80.0
    assert condition["risk_classification"] == "SAFE"


def test_multiple_potholes_increase_condition_risk():
    condition = compute_road_condition(
        potholes_count=4,
        total_damage_count=4,
        moderate_count=4,
        speed_limit=60,
        road_type="Arterial"
    )

    assert condition["condition_percentage"] < 50.0
    assert condition["risk_classification"] == "RISKY"
