"""
Belagavi boundaries, OSRM/OpenStreetMap road geometry, and route-risk evaluation.
"""
import json
import math
import os
import urllib.error
import urllib.parse
import urllib.request

from backend.duplicate_engine import haversine_distance_meters

BELAGAVI_SCOPE = "city"
BELAGAVI_BBOX = {
    "min_lat": 15.8050,
    "max_lat": 15.9250,
    "min_lon": 74.4600,
    "max_lon": 74.5700
}
BELAGAVI_CENTER = {
    "lat": 15.8497,
    "lon": 74.4977,
    "name": "Belagavi City Center",
    "state": "Karnataka",
    "country": "India"
}
BELAGAVI_CITY_POLYGON = [
    [74.4600, 15.8950],
    [74.5200, 15.9250],
    [74.5700, 15.8900],
    [74.5700, 15.8200],
    [74.5450, 15.8050],
    [74.4800, 15.8050],
    [74.4550, 15.8450],
    [74.4600, 15.8950]
]

OSRM_DEFAULT_URL = "https://router.project-osrm.org"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
OSRM_ATTRIBUTION = "Routing by OSRM using OpenStreetMap road data"
ROUTE_MATCH_DISTANCE_M = 35.0
SEGMENT_MATCH_DISTANCE_M = 25.0


class RoutingServiceError(Exception):
    """The configured OSRM service could not return a valid route response."""


class NoRouteError(Exception):
    """OSRM is available but found no drivable route for the selected points."""


def is_within_belagavi(lat: float, lon: float) -> bool:
    """Check a coordinate against the configured Belagavi City boundary."""
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(lat) or not math.isfinite(lon):
        return False
    if not (
        BELAGAVI_BBOX["min_lat"] <= lat <= BELAGAVI_BBOX["max_lat"]
        and BELAGAVI_BBOX["min_lon"] <= lon <= BELAGAVI_BBOX["max_lon"]
    ):
        return False

    inside = False
    previous_lon, previous_lat = BELAGAVI_CITY_POLYGON[0]
    for current_lon, current_lat in BELAGAVI_CITY_POLYGON[1:]:
        if (current_lat > lat) != (previous_lat > lat):
            crossing_lon = (
                (previous_lon - current_lon) * (lat - current_lat)
                / (previous_lat - current_lat)
                + current_lon
            )
            if lon < crossing_lon:
                inside = not inside
        previous_lon, previous_lat = current_lon, current_lat
    return inside


def _load_osm_road_catalog():
    catalog_path = os.path.join(os.path.dirname(__file__), "osm_road_corridors.json")
    try:
        with open(catalog_path, "r", encoding="utf-8") as catalog_file:
            catalog = json.load(catalog_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load the OSM road catalog at {catalog_path}: {exc}") from exc

    if not isinstance(catalog.get("roads"), list) or not 30 <= len(catalog["roads"]) <= 40:
        raise RuntimeError("The OSM road catalog must contain 30–40 real road corridors.")

    roads = []
    for road in catalog["roads"]:
        coordinates = road.get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise RuntimeError(f"OSM corridor {road.get('code')} has no valid line geometry.")
        if any(
            not isinstance(point, list)
            or len(point) != 2
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in point)
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
            for point in coordinates
        ):
            raise RuntimeError(f"OSM corridor {road.get('code')} contains invalid coordinates.")
        if not road.get("length_m") or road["length_m"] <= 0:
            raise RuntimeError(f"OSM corridor {road.get('code')} has an invalid length.")
        roads.append({
            **road,
            "geometry_source": catalog.get("source", OSRM_ATTRIBUTION),
            "geometry_updated_at": catalog.get("retrieved_at")
        })
    return roads


BELAGAVI_ROAD_SEGMENTS = _load_osm_road_catalog()


def point_to_segment_distance_meters(lat, lon, lat1, lon1, lat2, lon2):
    """Return a local-meter projection distance from a GPS point to a line segment."""
    reference_lat = math.radians(lat)
    meters_per_degree = 111320.0
    scale_x = math.cos(reference_lat) * meters_per_degree
    scale_y = meters_per_degree
    px, py = lon * scale_x, lat * scale_y
    x1, y1 = lon1 * scale_x, lat1 * scale_y
    x2, y2 = lon2 * scale_x, lat2 * scale_y
    dx, dy = x2 - x1, y2 - y1
    length_squared = dx * dx + dy * dy
    if length_squared == 0:
        distance = haversine_distance_meters(lat, lon, lat1, lon1)
        return distance if distance is not None else float("inf")
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_squared))
    projected_lon = (x1 + t * dx) / scale_x
    projected_lat = (y1 + t * dy) / scale_y
    distance = haversine_distance_meters(lat, lon, projected_lat, projected_lon)
    return distance if distance is not None else float("inf")


def _segment_coordinates(segment):
    if isinstance(segment, dict):
        return segment.get("coordinates") or []
    if not segment.geometry_geojson:
        return []
    try:
        return json.loads(segment.geometry_geojson)
    except (TypeError, json.JSONDecodeError):
        return []


def _distance_to_polyline_meters(lat, lon, coordinates):
    if len(coordinates) == 1:
        return haversine_distance_meters(lat, lon, coordinates[0][1], coordinates[0][0])
    minimum = float("inf")
    for first, second in zip(coordinates, coordinates[1:]):
        distance = point_to_segment_distance_meters(
            lat, lon, first[1], first[0], second[1], second[0]
        )
        minimum = min(minimum, distance)
    return minimum


def match_defect_to_belagavi_segment(lat, lon, max_buffer_m=50.0, segments=None):
    """Match GPS damage to the nearest actual OSM corridor within a distance threshold."""
    if isinstance(max_buffer_m, (list, tuple)):
        segments = max_buffer_m
        max_buffer_m = 50.0
    try:
        lat, lon = float(lat), float(lon)
        max_buffer_m = float(max_buffer_m)
    except (TypeError, ValueError):
        return None, None
    if not math.isfinite(lat) or not math.isfinite(lon) or max_buffer_m < 0:
        return None, None

    best_segment = None
    minimum_distance = float("inf")
    for segment in segments if segments is not None else BELAGAVI_ROAD_SEGMENTS:
        coordinates = _segment_coordinates(segment)
        if len(coordinates) < 2:
            continue
        distance = _distance_to_polyline_meters(lat, lon, coordinates)
        if distance < minimum_distance:
            minimum_distance = distance
            best_segment = segment
    if best_segment is None:
        return None, None
    return best_segment, round(minimum_distance, 1)


def _osrm_base_url():
    return os.environ.get("ROADVISION_OSRM_URL", OSRM_DEFAULT_URL).strip().rstrip("/")


def fetch_osrm_route_data(origin_lat, origin_lon, dest_lat, dest_lon):
    """Request real driving alternatives and their full GeoJSON from OSRM."""
    coordinates = (origin_lat, origin_lon, dest_lat, dest_lon)
    try:
        coordinates = tuple(float(value) for value in coordinates)
    except (TypeError, ValueError) as exc:
        raise ValueError("Origin and destination must be valid numeric coordinates.") from exc
    if not all(math.isfinite(value) for value in coordinates):
        raise ValueError("Origin and destination must be finite numeric coordinates.")

    origin_lat, origin_lon, dest_lat, dest_lon = coordinates
    if not is_within_belagavi(origin_lat, origin_lon):
        raise ValueError("Origin coordinate is outside the configured Belagavi City boundary.")
    if not is_within_belagavi(dest_lat, dest_lon):
        raise ValueError("Destination coordinate is outside the configured Belagavi City boundary.")
    if haversine_distance_meters(origin_lat, origin_lon, dest_lat, dest_lon) < 1:
        raise ValueError("Origin and destination must be distinct road locations.")

    base_url = _osrm_base_url()
    if not base_url.startswith(("http://", "https://")):
        raise RoutingServiceError("ROADVISION_OSRM_URL must be an HTTP or HTTPS URL.")
    try:
        timeout = float(os.environ.get("ROADVISION_OSRM_TIMEOUT", "12"))
    except ValueError as exc:
        raise RoutingServiceError("ROADVISION_OSRM_TIMEOUT must be a positive number.") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise RoutingServiceError("ROADVISION_OSRM_TIMEOUT must be a positive number.")

    path = (
        f"/route/v1/driving/{origin_lon:.6f},{origin_lat:.6f};"
        f"{dest_lon:.6f},{dest_lat:.6f}"
    )
    query = urllib.parse.urlencode({
        "alternatives": "3",
        "overview": "full",
        "geometries": "geojson",
        "steps": "true"
    })
    request = urllib.request.Request(
        f"{base_url}{path}?{query}",
        headers={"User-Agent": "ROADVISION-AI/1.0 (OSM road-risk routing)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            error_payload = {}
        if error_payload.get("code") == "NoRoute":
            raise NoRouteError("OSRM found no drivable route between these locations.") from exc
        raise RoutingServiceError(
            f"OSRM returned HTTP {exc.code}: {error_payload.get('message') or exc.reason}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RoutingServiceError(f"OSRM routing service is unavailable: {exc}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RoutingServiceError("OSRM returned an invalid JSON response.") from exc

    if not isinstance(payload, dict):
        raise RoutingServiceError("OSRM returned an invalid response document.")
    if payload.get("code") == "NoRoute":
        raise NoRouteError("OSRM found no drivable route between these locations.")
    if payload.get("code") != "Ok":
        raise RoutingServiceError(
            f"OSRM could not calculate routes: {payload.get('message') or payload.get('code', 'unknown error')}."
        )
    routes = payload.get("routes")
    waypoints = payload.get("waypoints")
    if not isinstance(routes, list) or not routes or not isinstance(waypoints, list) or len(waypoints) != 2:
        raise RoutingServiceError("OSRM returned an incomplete route response.")

    snapped_points = []
    for waypoint in waypoints:
        location = waypoint.get("location") if isinstance(waypoint, dict) else None
        if (
            not isinstance(location, list)
            or len(location) != 2
            or not all(
                isinstance(value, (int, float))
                and math.isfinite(value)
                for value in location
            )
            or not -180 <= location[0] <= 180
            or not -90 <= location[1] <= 90
        ):
            raise RoutingServiceError("OSRM returned invalid snapped route endpoints.")
        snapped_points.append(location)

    unique_routes = []
    signatures = set()
    for route in routes[:5]:
        if not isinstance(route, dict):
            raise RoutingServiceError("OSRM returned an invalid route entry.")
        geometry = route.get("geometry")
        route_coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if (
            not isinstance(route_coordinates, list)
            or len(route_coordinates) < 2
            or geometry.get("type") != "LineString"
            or not all(
                isinstance(point, list)
                and len(point) == 2
                and all(isinstance(value, (int, float)) and math.isfinite(value) for value in point)
                and -180 <= point[0] <= 180
                and -90 <= point[1] <= 90
                for point in route_coordinates
            )
            or not isinstance(route.get("distance"), (int, float))
            or not math.isfinite(route["distance"])
            or route["distance"] <= 0
            or not isinstance(route.get("duration"), (int, float))
            or not math.isfinite(route["duration"])
            or route["duration"] < 0
        ):
            raise RoutingServiceError("OSRM returned an invalid route geometry, distance, or duration.")
        if (
            haversine_distance_meters(
                route_coordinates[0][1],
                route_coordinates[0][0],
                snapped_points[0][1],
                snapped_points[0][0]
            ) > 100
            or haversine_distance_meters(
                route_coordinates[-1][1],
                route_coordinates[-1][0],
                snapped_points[1][1],
                snapped_points[1][0]
            ) > 100
        ):
            raise RoutingServiceError("OSRM route geometry does not connect to its reported snapped endpoints.")
        signature = tuple((round(point[0], 6), round(point[1], 6)) for point in route_coordinates)
        if signature in signatures:
            continue
        signatures.add(signature)
        unique_routes.append(route)
    if not unique_routes:
        raise RoutingServiceError("OSRM returned no distinct route geometries.")
    payload["routes"] = unique_routes
    return payload


def _route_road_names(route):
    names = []
    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            name = (step.get("name") or step.get("ref") or "").strip()
            if name and name.lower() != "unnamed road" and name not in names:
                names.append(name)
    return names


def _segment_route_coverage(segment_coordinates, route_coordinates):
    if len(segment_coordinates) < 2:
        return 0.0
    stride = max(1, math.ceil(len(segment_coordinates) / 40))
    samples = segment_coordinates[::stride]
    if samples[-1] != segment_coordinates[-1]:
        samples.append(segment_coordinates[-1])
    covered = sum(
        1
        for lon, lat in samples
        if _distance_to_polyline_meters(lat, lon, route_coordinates) <= SEGMENT_MATCH_DISTANCE_M
    )
    return covered / len(samples)


def evaluate_route_risk(route, verified_defects, segment_conditions=None, route_index=1):
    """Score an OSRM route against verified damage and matching database road corridors."""
    route_coordinates = route["geometry"]["coordinates"]
    total_length_m = float(route["distance"])
    total_km = round(total_length_m / 1000.0, 2)

    matched_defects = []
    severe_count = moderate_count = minor_count = pothole_count = 0
    for defect in verified_defects:
        try:
            latitude = float(defect["lat"])
            longitude = float(defect["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(latitude) or not math.isfinite(longitude):
            continue
        distance = _distance_to_polyline_meters(latitude, longitude, route_coordinates)
        if distance > ROUTE_MATCH_DISTANCE_M:
            continue
        matched = {**defect, "distance_to_route_m": round(distance, 1)}
        matched_defects.append(matched)
        severity = str(defect.get("severity", "Minor")).lower()
        if severity == "severe":
            severe_count += 1
        elif severity == "moderate":
            moderate_count += 1
        else:
            minor_count += 1
        if defect.get("category_code") == "D40":
            pothole_count += 1

    segments_summary = []
    risky_segments = moderate_segments = safe_segments = 0
    for segment_id, condition in (segment_conditions or {}).items():
        coordinates = condition.get("coordinates") or []
        if _segment_route_coverage(coordinates, route_coordinates) < 0.25:
            continue
        condition_pct = float(condition.get("condition_percentage", 100.0))
        risk_class = str(condition.get("risk_classification", "SAFE")).upper()
        potholes = int(condition.get("potholes_count", 0) or 0)
        if risk_class == "RISKY" or condition_pct < 50:
            risk_class, color = "RISKY", "#dc2626"
            risky_segments += 1
        elif risk_class == "MODERATE" or condition_pct < 80:
            risk_class, color = "MODERATE", "#d97706"
            moderate_segments += 1
        else:
            risk_class, color = "SAFE", "#059669"
            safe_segments += 1
        segments_summary.append({
            "id": condition.get("id", segment_id),
            "code": condition.get("code"),
            "name": condition.get("name", "OSM road corridor"),
            "length_m": condition.get("length_m"),
            "coverage_percent": round(_segment_route_coverage(coordinates, route_coordinates) * 100, 1),
            "condition_percentage": condition_pct,
            "potholes_count": potholes,
            "risk_classification": risk_class,
            "risk_color": color,
            "is_risky": risk_class == "RISKY"
        })

    total_defects = len(matched_defects)
    density_per_km = total_defects / max(total_km, 0.5)
    severity_points = minor_count * 3 + moderate_count * 8 + severe_count * 20
    segment_penalty = risky_segments * 18.0 + moderate_segments * 5.0
    hazard_multiplier = 1.0 + severe_count * 0.25 + risky_segments * 0.20
    exposure = min(
        100.0,
        ((severity_points * 1.5 + density_per_km * 4.0) + segment_penalty) * hazard_multiplier
    )
    exposure_score = round(exposure, 1)

    if exposure_score >= 60 or risky_segments:
        risk_level = "Critical" if exposure_score >= 65 else "High"
        risk_color = "#dc2626"
        risk_bg = "bg-rose-100 text-rose-800 border-rose-300"
    elif exposure_score >= 25 or moderate_segments:
        risk_level = "Moderate"
        risk_color = "#d97706"
        risk_bg = "bg-amber-100 text-amber-800 border-amber-300"
    else:
        risk_level = "Low"
        risk_color = "#059669"
        risk_bg = "bg-emerald-100 text-emerald-800 border-emerald-300"

    road_names = _route_road_names(route)
    route_name = ", ".join(road_names[:3]) if road_names else f"OSM road route {route_index}"
    factors = []
    for segment in segments_summary:
        if segment["is_risky"]:
            factors.append(
                f"High-risk corridor '{segment['name']}' has {segment['potholes_count']} active potholes "
                f"and {segment['condition_percentage']}% condition."
            )
    if total_defects:
        factors.append(
            f"{total_defects} verified damage record(s) within {ROUTE_MATCH_DISTANCE_M:.0f} m "
            f"of this route, including {pothole_count} pothole(s)."
        )
        if severe_count:
            factors.append(f"{severe_count} severe verified damage record(s) are near the route.")
    if not factors:
        factors.append("No active verified damage records matched this route; unreported hazards may still be present.")

    return {
        "name": route_name,
        "color": risk_color,
        "border_color": risk_color,
        "color_name": f"{risk_level} road risk",
        "tag": f"{risk_level} risk route",
        "distance_m": round(total_length_m, 1),
        "distance_km": total_km,
        "duration_s": round(float(route["duration"]), 1),
        "estimated_time_min": round(float(route["duration"]) / 60.0, 1),
        "total_defects": total_defects,
        "potholes_count": pothole_count,
        "severe_defects": severe_count,
        "moderate_defects": moderate_count,
        "minor_defects": minor_count,
        "risky_segments_count": risky_segments,
        "moderate_segments_count": moderate_segments,
        "safe_segments_count": safe_segments,
        "exposure_score": exposure_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_bg": risk_bg,
        "factors": factors,
        "geometry": route["geometry"],
        "polyline": [[point[1], point[0]] for point in route_coordinates],
        "matched_defects": matched_defects,
        "segments": segments_summary
    }


def recommend_best_route(origin_lat, origin_lon, dest_lat, dest_lon, verified_defects, segment_conditions=None):
    """Get actual OSRM driving alternatives and rank them by distance and verified road risk."""
    for label, latitude, longitude in (
        ("Origin", origin_lat, origin_lon),
        ("Destination", dest_lat, dest_lon)
    ):
        if not is_within_belagavi(latitude, longitude):
            return {
                "status": "error",
                "message": f"{label} coordinate is outside the configured Belagavi City boundary."
            }
    if haversine_distance_meters(origin_lat, origin_lon, dest_lat, dest_lon) < 1:
        return {"status": "error", "message": "Origin and destination must be distinct road locations."}

    payload = fetch_osrm_route_data(origin_lat, origin_lon, dest_lat, dest_lon)
    routes = [
        evaluate_route_risk(route, verified_defects, segment_conditions, index)
        for index, route in enumerate(payload["routes"], start=1)
    ]
    for route in routes:
        route["recommendation_score"] = round(
            route["distance_km"] + 0.05 * route["exposure_score"], 2
        )
    routes.sort(key=lambda route: (route["recommendation_score"], route["distance_km"]))

    for index, route in enumerate(routes, start=1):
        route["route_id"] = index
        route["is_recommended"] = index == 1
        route["color_label"] = f"{route['risk_level']} road risk"
        route["summary_badge"] = (
            "Recommended: lowest distance/risk score"
            if index == 1
            else f"Alternative {index - 1} · {route['risk_level']} risk"
        )
        route["name"] = f"Route {index}: via {route['name']}"

    recommended = routes[0]
    if len(routes) == 1:
        comparison = "OSRM returned one drivable route; no distinct alternatives were available for this pair."
    else:
        comparison = (
            f"Recommended by the lowest transparent score "
            f"(distance in km + 0.05 × verified exposure points): "
            f"{recommended['distance_km']} km, {recommended['exposure_score']}/100 exposure."
        )

    origin_waypoint, destination_waypoint = payload["waypoints"]
    origin_snap = origin_waypoint["location"]
    destination_snap = destination_waypoint["location"]
    return {
        "status": "success",
        "origin": {
            "lat": origin_snap[1],
            "lon": origin_snap[0],
            "junction": origin_waypoint.get("name") or "OSRM-snapped road point",
            "requested_lat": float(origin_lat),
            "requested_lon": float(origin_lon)
        },
        "destination": {
            "lat": destination_snap[1],
            "lon": destination_snap[0],
            "junction": destination_waypoint.get("name") or "OSRM-snapped road point",
            "requested_lat": float(dest_lat),
            "requested_lon": float(dest_lon)
        },
        "recommended_route_id": recommended["route_id"],
        "routing_engine": "OSRM",
        "osm_attribution": OSM_ATTRIBUTION,
        "route_count": len(routes),
        "max_routes_requested": 3,
        "scoring_method": "distance_km + 0.05 × exposure_score",
        "comparison_summary": comparison,
        "disclaimer": (
            "Routes follow the live OSRM/OpenStreetMap driving network. Risk uses verified database "
            "records within 35 m of each route and matching road-corridor condition records."
        ),
        "routes": routes
    }
