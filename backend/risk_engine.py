"""
ROADVISION AI - Intelligent Explainable Road Risk Assessment Engine
Computes a normalized 0-100 Infrastructure Risk Score considering defect density,
severity tiers, damage types, road classification, speed limits, traffic, and weather.
"""
from backend.config import RISK_WEIGHTS

def calculate_road_risk_score(
    defects,
    road_type="Arterial",
    speed_limit=60,
    traffic_volume="Moderate",
    weather_condition="Clear/Dry"
):
    """
    Computes an explainable 0-100 Road Risk Score.
    Returns:
        score (float: 0.0 - 100.0),
        level (str: "Low", "Moderate", "High", "Critical"),
        breakdown (dict: details of each component)
    """
    if not defects:
        return 0.0, "Low", {
            "base_damage_score": 0.0,
            "density_factor": 1.0,
            "road_multiplier": 1.0,
            "speed_multiplier": 1.0,
            "weather_multiplier": 1.0,
            "traffic_multiplier": 1.0,
            "contributing_factors": ["No defects detected on surveyed road segment."]
        }

    # 1. Base Damage Calculation from individual defects
    severity_weights = RISK_WEIGHTS["severity"]
    category_weights = RISK_WEIGHTS["category"]

    defect_scores = []
    category_counts = {"D00": 0, "D10": 0, "D20": 0, "D40": 0}
    severity_counts = {"Minor": 0, "Moderate": 0, "Severe": 0}

    for d in defects:
        sev = d.get("severity", "Minor")
        cat = d.get("category_code", "D40")

        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        category_counts[cat] = category_counts.get(cat, 0) + 1

        s_val = severity_weights.get(sev, 10)
        c_mult = category_weights.get(cat, 1.0)
        defect_scores.append(s_val * c_mult)

    # Sublinear accumulation to prevent unbounded runaway on long video segments
    total_raw = sum(defect_scores)
    # Scaled base (0 to 60 points max from defects)
    base_score = min(60.0, total_raw * 0.45)

    # 2. Defect Density Factor
    count = len(defects)
    density_factor = 1.0
    if count >= 8:
        density_factor = 1.35
    elif count >= 4:
        density_factor = 1.20
    elif count >= 2:
        density_factor = 1.08

    # 3. Road Classification Multiplier
    road_multiplier = RISK_WEIGHTS["road_class"].get(road_type, 1.0)

    # 4. Speed Limit Multiplier (Higher speed = greater vehicle impact risk)
    if speed_limit >= 90:
        speed_multiplier = 1.30
    elif speed_limit >= 70:
        speed_multiplier = 1.18
    elif speed_limit >= 50:
        speed_multiplier = 1.05
    else:
        speed_multiplier = 0.90

    # 5. Traffic Volume Multiplier
    traffic_map = {"High": 1.20, "Moderate": 1.05, "Low": 0.90}
    traffic_multiplier = traffic_map.get(traffic_volume, 1.0)

    # 6. Weather Condition Multiplier (Rain / wet asphalt increases hydroplaning)
    weather_multiplier = RISK_WEIGHTS["weather"].get(weather_condition, 1.0)

    # Composite normalized calculation
    composite = base_score * density_factor * road_multiplier * speed_multiplier * traffic_multiplier * weather_multiplier

    # Severe pothole bonus: any severe pothole on high speed road enforces minimum 65 score
    if severity_counts.get("Severe", 0) > 0 and category_counts.get("D40", 0) > 0:
        composite = max(composite, 62.0)

    final_score = round(max(0.0, min(100.0, composite)), 1)

    # Categorization into 4 tiers
    if final_score <= 25.0:
        risk_level = "Low"
    elif final_score <= 50.0:
        risk_level = "Moderate"
    elif final_score <= 75.0:
        risk_level = "High"
    else:
        risk_level = "Critical"

    # Explainable narrative points
    reasons = []
    if category_counts["D40"] > 0:
        reasons.append(f"{category_counts['D40']} pothole(s) detected with high tire puncture and suspension impact risk")
    if category_counts["D20"] > 0:
        reasons.append(f"{category_counts['D20']} alligator fatigue crack cluster(s) indicating sub-base pavement failure")
    if severity_counts["Severe"] > 0:
        reasons.append(f"{severity_counts['Severe']} defect(s) classified as Severe requiring urgent intervention")
    if speed_limit >= 70:
        reasons.append(f"High-speed corridor ({speed_limit} km/h) escalates collision and loss-of-control hazard")
    if "Rain" in weather_condition or "Wet" in weather_condition:
        reasons.append(f"Wet surface conditions exacerbate water ingress and hydroplaning risk")
    if road_type in ["Highway", "Arterial"]:
        reasons.append(f"Major arterial transport route carries heavy axle loads")

    breakdown = {
        "raw_damage_score": round(total_raw, 1),
        "base_damage_score": round(base_score, 1),
        "density_factor": density_factor,
        "road_multiplier": road_multiplier,
        "speed_multiplier": speed_multiplier,
        "traffic_multiplier": traffic_multiplier,
        "weather_multiplier": weather_multiplier,
        "defect_counts": category_counts,
        "severity_counts": severity_counts,
        "contributing_factors": reasons
    }

    return final_score, risk_level, breakdown
