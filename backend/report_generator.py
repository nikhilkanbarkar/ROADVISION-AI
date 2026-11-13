"""
ROADVISION AI - Multi-Format Inspection Report Generator
Generates comprehensive PDF/HTML, CSV, and JSON reports with detailed metrics,
risk breakdowns, defect inventories, and municipal repair action plans.
"""
import os
import csv
import json
from datetime import datetime
from backend.config import REPORTS_DIR

def generate_json_report(inspection, defects, risk_breakdown=None):
    """Generates a structured JSON inspection report."""
    rep_name = f"report_{inspection.code}.json"
    rep_path = os.path.join(REPORTS_DIR, rep_name)

    defect_items = []
    for d in defects:
        defect_items.append({
            "defect_id": d.id,
            "track_id": d.track_id,
            "category_code": d.category_code,
            "class_name": d.class_name,
            "display_name": d.class_name.replace("_", " ").title(),
            "confidence": d.confidence,
            "severity": d.severity,
            "estimated_depth": d.estimated_depth_tier,
            "bbox": [d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
            "relative_area_pct": round((d.relative_area or 0.0) * 100, 2),
            "verification_status": d.verification_status,
            "latitude": d.latitude,
            "longitude": d.longitude
        })

    data = {
        "platform": "ROADVISION AI",
        "report_id": f"REP-{inspection.code}",
        "generated_at": datetime.utcnow().isoformat(),
        "inspection_details": {
            "code": inspection.code,
            "title": inspection.title,
            "media_type": inspection.media_type,
            "survey_date": inspection.upload_time.isoformat() if inspection.upload_time else None,
            "road_name": inspection.road_name,
            "road_type": inspection.road_type,
            "speed_limit_kmh": inspection.speed_limit,
            "weather": inspection.weather_condition,
            "traffic_volume": inspection.traffic_volume,
            "latitude": inspection.latitude,
            "longitude": inspection.longitude
        },
        "summary_metrics": {
            "total_detections": inspection.total_detections,
            "unique_defects_count": inspection.unique_defects_count,
            "severity_breakdown": {
                "minor": inspection.minor_count,
                "moderate": inspection.moderate_count,
                "severe": inspection.severe_count
            },
            "infrastructure_risk_score": inspection.risk_score,
            "risk_tier": inspection.risk_level
        },
        "risk_breakdown": risk_breakdown or {},
        "defects": defect_items
    }

    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return rep_path

def generate_csv_report(inspection, defects):
    """Generates a tabular CSV defect inventory report."""
    rep_name = f"report_{inspection.code}.csv"
    rep_path = os.path.join(REPORTS_DIR, rep_name)

    headers = [
        "Defect_ID", "Inspection_Code", "Track_ID", "Category_Code",
        "Damage_Class", "Confidence", "Severity", "Depth_Tier",
        "Relative_Area_Pct", "BBox_X1", "BBox_Y1", "BBox_X2", "BBox_Y2",
        "Verification_Status", "Latitude", "Longitude", "Road_Name"
    ]

    with open(rep_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for d in defects:
            writer.writerow([
                d.id,
                inspection.code,
                d.track_id,
                d.category_code,
                d.class_name,
                d.confidence,
                d.severity,
                d.estimated_depth_tier,
                round((d.relative_area or 0.0) * 100, 2),
                d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2,
                d.verification_status,
                d.latitude or inspection.latitude or "",
                d.longitude or inspection.longitude or "",
                inspection.road_name
            ])

    return rep_path

def generate_html_report(inspection, defects, risk_breakdown=None):
    """Generates a standalone, beautifully formatted printable HTML/PDF report."""
    rep_name = f"report_{inspection.code}.html"
    rep_path = os.path.join(REPORTS_DIR, rep_name)

    risk_color = "#10B981" # Green
    if inspection.risk_level == "Moderate":
        risk_color = "#F59E0B" # Orange
    elif inspection.risk_level in ["High", "Critical"]:
        risk_color = "#EF4444" # Red

    defect_rows = ""
    for idx, d in enumerate(defects, 1):
        sev_color = "#10B981" if d.severity == "Minor" else ("#F59E0B" if d.severity == "Moderate" else "#EF4444")
        defect_rows += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{idx}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 12px;">{d.track_id or 'N/A'}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0; font-weight: 600;">{d.category_code}: {d.class_name.replace('_', ' ').title()}</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{(d.confidence or 0)*100:.1f}%</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;"><span style="color: {sev_color}; font-weight: 700;">{d.severity}</span></td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{round((d.relative_area or 0.0)*100, 2)}%</td>
            <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{d.verification_status}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ROADVISION AI - Inspection Report {inspection.code}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; color: #1e293b; margin: 0; padding: 30px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #ffffff; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; }}
        .title {{ font-size: 26px; font-weight: 800; color: #0f172a; margin: 0; }}
        .tagline {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
        .badge {{ background: #0284c7; color: white; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 14px; }}
        .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 25px 0; background: #f1f5f9; padding: 20px; border-radius: 8px; }}
        .meta-item {{ font-size: 13px; }}
        .meta-label {{ color: #64748b; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
        .meta-value {{ color: #0f172a; font-weight: 700; margin-top: 2px; font-size: 14px; }}
        .kpi-container {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .kpi-card {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 16px; text-align: center; }}
        .kpi-num {{ font-size: 28px; font-weight: 800; color: #0f172a; margin: 4px 0; }}
        .kpi-label {{ font-size: 12px; color: #64748b; font-weight: 600; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }}
        th {{ background: #f8fafc; padding: 12px 10px; text-align: left; font-size: 12px; color: #475569; text-transform: uppercase; border-bottom: 2px solid #cbd5e1; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
        @media print {{ body {{ background: white; padding: 0; }} .container {{ box-shadow: none; padding: 0; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">ROADVISION AI</h1>
                <div class="tagline">Intelligent Road Damage Detection & Infrastructure Intelligence</div>
            </div>
            <div>
                <span class="badge">{inspection.code}</span>
            </div>
        </div>

        <div class="meta-grid">
            <div class="meta-item"><div class="meta-label">Survey Date</div><div class="meta-value">{inspection.upload_time.strftime('%Y-%m-%d %H:%M') if inspection.upload_time else 'N/A'}</div></div>
            <div class="meta-item"><div class="meta-label">Road Location</div><div class="meta-value">{inspection.road_name} ({inspection.location_name})</div></div>
            <div class="meta-item"><div class="meta-label">Coordinates</div><div class="meta-value">{inspection.latitude or 'N/A'}, {inspection.longitude or 'N/A'}</div></div>
            <div class="meta-item"><div class="meta-label">Road Type</div><div class="meta-value">{inspection.road_type} (Speed: {inspection.speed_limit} km/h)</div></div>
            <div class="meta-item"><div class="meta-label">Weather / Traffic</div><div class="meta-value">{inspection.weather_condition} | {inspection.traffic_volume} Traffic</div></div>
            <div class="meta-item"><div class="meta-label">Media Type</div><div class="meta-value">{inspection.media_type.upper()} Inspection</div></div>
        </div>

        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-label">Total Detections</div>
                <div class="kpi-num">{inspection.total_detections}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Unique Defects</div>
                <div class="kpi-num">{inspection.unique_defects_count}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Severe Defects</div>
                <div class="kpi-num" style="color: #ef4444;">{inspection.severe_count}</div>
            </div>
            <div class="kpi-card" style="border-left: 4px solid {risk_color};">
                <div class="kpi-label">Infrastructure Risk</div>
                <div class="kpi-num" style="color: {risk_color};">{inspection.risk_score} / 100</div>
                <div style="font-size: 11px; font-weight: 700; color: {risk_color};">{inspection.risk_level.upper()} RISK</div>
            </div>
        </div>

        <h3 style="font-size: 16px; margin-bottom: 6px; color: #0f172a;">Defect Inventory and Damage Classification</h3>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Track ID</th>
                    <th>Damage Type</th>
                    <th>Confidence</th>
                    <th>Severity</th>
                    <th>Relative Area</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {defect_rows if defect_rows else '<tr><td colspan=\"7\" style=\"text-align:center; padding: 20px; color: #94a3b8;\">No defects recorded. Road surface in sound condition.</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            Generated autonomously by ROADVISION AI &bull; Municipal Infrastructure Maintenance Division &bull; Confidential
        </div>
    </div>
</body>
</html>"""

    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(html)

    return rep_path
