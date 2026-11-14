"""Refresh the bundled Belagavi road geometry snapshot from OSRM."""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--url",
    default=os.environ.get("ROADVISION_OSRM_URL", "https://router.project-osrm.org"),
    help="OSRM-compatible routing service URL"
)
parser.add_argument(
    "--output",
    default=os.path.join(ROOT_DIR, "backend", "osm_road_corridors.json"),
    help="Output path for the refreshed road catalog"
)
parser.add_argument(
    "--delay",
    type=float,
    default=1.0,
    help="Seconds to wait between requests to respect public routing-service limits"
)
args = parser.parse_args()

if args.delay < 0:
    parser.error("--delay must be zero or greater")
os.environ["ROADVISION_OSRM_URL"] = args.url

from backend.gis_belagavi import (  # noqa: E402
    BELAGAVI_ROAD_SEGMENTS,
    OSM_ATTRIBUTION,
    fetch_osrm_route_data,
)


def route_names(route):
    names = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            name = (step.get("name") or step.get("ref") or "").strip()
            if name and name.lower() != "unnamed road" and name not in names:
                names.append(name)
    return names


roads = []
for index, road in enumerate(BELAGAVI_ROAD_SEGMENTS, start=1):
    start = road["coordinates"][0]
    end = road["coordinates"][-1]
    response = fetch_osrm_route_data(start[1], start[0], end[1], end[0])
    route = response["routes"][0]
    start_snap, end_snap = [waypoint["location"] for waypoint in response["waypoints"]]
    roads.append({
        "id": road["id"],
        "code": road["code"],
        "name": road["name"],
        "osm_names": route_names(route),
        "road_type": road.get("road_type") or "Road",
        "speed_limit": road.get("speed_limit") or 50,
        "surface": road.get("surface") or "Unknown",
        "start": start_snap,
        "end": end_snap,
        "length_m": round(float(route["distance"]), 1),
        "duration_s": round(float(route["duration"]), 1),
        "coordinates": route["geometry"]["coordinates"]
    })
    print(f"[{index}/{len(BELAGAVI_ROAD_SEGMENTS)}] {road['code']}: {len(route['geometry']['coordinates'])} OSM points")
    if index < len(BELAGAVI_ROAD_SEGMENTS):
        time.sleep(args.delay)

catalog = {
    "source": "OSRM routing over OpenStreetMap road data",
    "attribution": OSM_ATTRIBUTION,
    "routing_service": args.url.rstrip("/"),
    "retrieved_at": datetime.now(timezone.utc).isoformat(),
    "roads": roads
}
output_path = Path(args.output).resolve()
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(catalog, separators=(",", ":")), encoding="utf-8")
print(f"Updated {len(roads)} OSM corridors at {output_path}")
