"""
ROADVISION AI - Historical Road Condition and Deterioration Monitoring Engine
Compares time-separated inspections of the same road location to track deterioration,
stability, or repair completion, generating side-by-side visual evidence.
"""
import os
import cv2
import numpy as np
from datetime import datetime
from backend.duplicate_engine import haversine_distance_meters
from backend.config import OUTPUTS_DIR

def generate_side_by_side_comparison(img1_path, img2_path, out_path, date1_str, date2_str, trend_label):
    """
    Creates a composite side-by-side visual comparison with header banners and metrics.
    """
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        return None

    # Resize both images to uniform height
    target_h = 500
    w1 = int(img1.shape[1] * (target_h / img1.shape[0]))
    w2 = int(img2.shape[1] * (target_h / img2.shape[0]))

    r_img1 = cv2.resize(img1, (w1, target_h))
    r_img2 = cv2.resize(img2, (w2, target_h))

    # Banner height
    banner_h = 70
    canvas_w = w1 + w2 + 10 # 10px divider
    canvas = np.zeros((target_h + banner_h, canvas_w, 3), dtype=np.uint8)

    # Fill banner
    banner_color = (30, 30, 35)
    cv2.rectangle(canvas, (0, 0), (canvas_w, banner_h), banner_color, -1)

    # Title & trend tag
    trend_color = (0, 0, 255) if trend_label == "Worsened" else ((0, 255, 0) if "Improved" in trend_label or "Repaired" in trend_label else (0, 200, 255))
    cv2.putText(canvas, f"HISTORICAL ROAD SURVEY COMPARISON | Status: {trend_label.upper()}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, trend_color, 2)
    cv2.putText(canvas, f"Earlier: {date1_str}  vs  Latest: {date2_str}", (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1)

    # Place images
    canvas[banner_h:banner_h + target_h, 0:w1] = r_img1
    canvas[banner_h:banner_h + target_h, w1 + 10:canvas_w] = r_img2

    # Divider line
    cv2.line(canvas, (w1 + 5, banner_h), (w1 + 5, banner_h + target_h), (80, 80, 80), 2)

    # Sub-labels
    cv2.putText(canvas, f"INSPECTION 1 (Baseline: {date1_str})", (20, banner_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(canvas, f"INSPECTION 2 (Current: {date2_str})", (w1 + 30, banner_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, canvas)
    return out_path

def compare_inspections(earlier_insp, later_insp, earlier_defects, later_defects):
    """
    Compares two temporal inspections of the same location.
    Returns structured analysis of condition trend, area delta, and generated comparison image.
    """
    days_elapsed = 0
    if earlier_insp.upload_time and later_insp.upload_time:
        days_elapsed = abs((later_insp.upload_time - earlier_insp.upload_time).days)

    earlier_count = len(earlier_defects)
    later_count = len(later_defects)

    earlier_area_sum = sum(d.relative_area or 0.0 for d in earlier_defects)
    later_area_sum = sum(d.relative_area or 0.0 for d in later_defects)

    if earlier_area_sum > 0:
        area_delta_pct = round(((later_area_sum - earlier_area_sum) / earlier_area_sum) * 100, 1)
    else:
        area_delta_pct = 100.0 if later_area_sum > 0 else 0.0

    # Determine condition trend
    if later_count == 0 and earlier_count > 0:
        trend = "Repaired / Improved"
        notes = f"All {earlier_count} previously detected road defects have been resolved or patched."
    elif area_delta_pct <= -25.0 or (later_count < earlier_count and area_delta_pct <= 0):
        trend = "Improved"
        notes = f"Road condition improved: total damaged area decreased by {abs(area_delta_pct)}%."
    elif area_delta_pct >= 20.0 or later_count > earlier_count or later_insp.severe_count > earlier_insp.severe_count:
        trend = "Worsened"
        notes = f"Active deterioration observed: damage area expanded by {area_delta_pct}% ({later_count - earlier_count} new defects)."
    else:
        trend = "Stable"
        notes = f"Defect dimensions and severity remain largely unchanged over {days_elapsed} days."

    # Generate visual side-by-side if annotated images exist
    side_by_side_path = None
    if earlier_insp.annotated_path and later_insp.annotated_path and os.path.exists(earlier_insp.annotated_path) and os.path.exists(later_insp.annotated_path):
        out_name = f"comparison_{earlier_insp.id}_{later_insp.id}.jpg"
        out_path = os.path.join(OUTPUTS_DIR, out_name)
        d1_str = earlier_insp.upload_time.strftime("%Y-%m-%d") if earlier_insp.upload_time else "Survey-1"
        d2_str = later_insp.upload_time.strftime("%Y-%m-%d") if later_insp.upload_time else "Survey-2"
        side_by_side_path = generate_side_by_side_comparison(
            earlier_insp.annotated_path,
            later_insp.annotated_path,
            out_path,
            d1_str,
            d2_str,
            trend
        )

    return {
        "days_elapsed": days_elapsed,
        "earlier_defect_count": earlier_count,
        "later_defect_count": later_count,
        "count_delta": later_count - earlier_count,
        "earlier_area_sum": round(earlier_area_sum, 4),
        "later_area_sum": round(later_area_sum, 4),
        "area_delta_pct": area_delta_pct,
        "condition_trend": trend,
        "side_by_side_path": side_by_side_path,
        "summary_notes": notes
    }
