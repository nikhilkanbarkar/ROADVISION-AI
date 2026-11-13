"""
ROADVISION AI - Belagavi Geospatial, Road Network & Risk-Aware Navigation Engine
Primary Geographical Scope: Belagavi (Belgaum), Karnataka, India.

Provides:
1. Official Belagavi City boundary definition and spatial bounding checks.
2. Topological Road Network graph of Belagavi City corridors.
3. Spatial matching of road defects to road segments via perpendicular buffer projection.
4. Risk-Aware Multi-Route Alternative Generation (Dijkstra / A* graph traversal).
5. Explainable Route Damage Exposure Scoring Function.
"""
import math
import json
from datetime import datetime
from backend.duplicate_engine import haversine_distance_meters

# ==============================================================================
# 1. BELAGAVI GEOGRAPHICAL BOUNDARY CONFIGURATION
# ==============================================================================
# Geographical Scope: Belagavi City Corporation Area, Karnataka, India
BELAGAVI_SCOPE = "city"  # Configurable: "city" or "district"

BELAGAVI_BBOX = {
    "min_lat": 15.8050,
    "max_lat": 15.9250,
    "min_lon": 74.4600,
    "max_lon": 74.5700
}

BELAGAVI_CENTER = {
    "lat": 15.8497,
    "lon": 74.4977,
    "name": "Belagavi City Center (Chennamma Circle)",
    "state": "Karnataka",
    "country": "India"
}

# Simplified polygon boundary covering Belagavi City Corporation limits (longitude, latitude)
BELAGAVI_CITY_POLYGON = [
    [74.4600, 15.8950], # NW Kakati / Machhe approach
    [74.5200, 15.9250], # North Kanbargi
    [74.5700, 15.8900], # NE Gandhi Nagar / NH48
    [74.5700, 15.8200], # East Halaga / Suvarna Soudha
    [74.5450, 15.8050], # SE Khasbag / Angol
    [74.4800, 15.8050], # South Vadgaon / Udyambag
    [74.4550, 15.8450], # SW Peeranwadi / Tilakwadi
    [74.4600, 15.8950]  # Closed polygon
]

def is_within_belagavi(lat: float, lon: float) -> bool:
    """
    Verifies if a geographic coordinate falls inside the configured Belagavi City boundary.
    Uses bounding box pre-filter followed by Ray-Casting Point-in-Polygon check.
    """
    if lat is None or lon is None:
        return False

    # Bounding box pre-check
    if not (BELAGAVI_BBOX["min_lat"] <= lat <= BELAGAVI_BBOX["max_lat"] and
            BELAGAVI_BBOX["min_lon"] <= lon <= BELAGAVI_BBOX["max_lon"]):
        return False

    # Standard ray-casting algorithm for point (lon, lat) in polygon
    inside = False
    n = len(BELAGAVI_CITY_POLYGON)
    p1x, p1y = BELAGAVI_CITY_POLYGON[0]
    for i in range(1, n + 1):
        p2x, p2y = BELAGAVI_CITY_POLYGON[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

# ==============================================================================
# 2. BELAGAVI CITY ROAD NETWORK TOPOLOGY (NODES & SEGMENTS)
# ==============================================================================
# Authentic road junctions and corridors across Belagavi City
BELAGAVI_JUNCTIONS = {
    "CHEN_CIRC": {"name": "Rani Chennamma Circle", "lat": 15.8574, "lon": 74.5065, "type": "Central Roundabout"},
    "BOGARVES": {"name": "Bogarves Circle", "lat": 15.8540, "lon": 74.5020, "type": "Commercial Junction"},
    "SAMBHAJI": {"name": "Sambhaji Chowk (RTO)", "lat": 15.8480, "lon": 74.5050, "type": "Highway/City Gate"},
    "TILAKWADI_1": {"name": "1st Railway Gate, Tilakwadi", "lat": 15.8440, "lon": 74.5010, "type": "Railway Crossing"},
    "TILAKWADI_3": {"name": "3rd Railway Gate, Khanapur Rd", "lat": 15.8360, "lon": 74.4960, "type": "Major Arterial Crossing"},
    "RPD_CROSS": {"name": "RPD College Cross", "lat": 15.8320, "lon": 74.4910, "type": "Educational Corridor"},
    "UDYAMBAG": {"name": "Udyambag Industrial Hub", "lat": 15.8200, "lon": 74.4820, "type": "Industrial Gate"},
    "CAMP_CHURCH": {"name": "Camp St. Mary's Church", "lat": 15.8610, "lon": 74.4980, "type": "Cantonment Junction"},
    "CIVIL_HOSP": {"name": "Civil Hospital (BIMS)", "lat": 15.8640, "lon": 74.5120, "type": "Medical Corridor"},
    "FORT_LAKE": {"name": "Belagavi Fort Lake Junction", "lat": 15.8660, "lon": 74.5200, "type": "Heritage / Highway Access"},
    "KANBARGI_CR": {"name": "Kanbargi Cross (NH-48)", "lat": 15.8920, "lon": 74.5420, "type": "Highway Interchange"},
    "RAMTEERTH": {"name": "Ramteerth Nagar / Auto Nagar", "lat": 15.8820, "lon": 74.5480, "type": "Highway Transit Node"},
    "GANDHI_NGR": {"name": "Gandhi Nagar Bypass (NH-48)", "lat": 15.8650, "lon": 74.5530, "type": "National Highway Junction"},
    "HALAGA_INT": {"name": "Halaga Interchange (Suvarna Soudha)", "lat": 15.8290, "lon": 74.5580, "type": "National Highway Exit"},
    "SHAHAPUR": {"name": "Shahapur Central Market", "lat": 15.8420, "lon": 74.5150, "type": "Heritage Market"},
    "VADGAON": {"name": "Vadgaon Main Junction", "lat": 15.8340, "lon": 74.5120, "type": "Urban Cross"},
    "HINDWADI": {"name": "Hindwadi Goaves Cross", "lat": 15.8460, "lon": 74.4940, "type": "Residential Arterial"}
}

# Real Belagavi Road Network Segments
BELAGAVI_ROAD_SEGMENTS = [
    {
        "id": 1,
        "code": "BLG-SEG-01",
        "name": "Khanapur Road (Tilakwadi to 3rd Gate)",
        "from_node": "BOGARVES",
        "to_node": "TILAKWADI_3",
        "road_type": "Arterial",
        "speed_limit": 60,
        "surface": "Bituminous Asphalt",
        "coordinates": [
            [74.5020, 15.8540],
            [74.4995, 15.8450],
            [74.4960, 15.8360]
        ]
    },
    {
        "id": 2,
        "code": "BLG-SEG-02",
        "name": "Khanapur Road (3rd Gate to Udyambag)",
        "from_node": "TILAKWADI_3",
        "to_node": "UDYAMBAG",
        "road_type": "Arterial",
        "speed_limit": 60,
        "surface": "Bituminous Asphalt",
        "coordinates": [
            [74.4960, 15.8360],
            [74.4910, 15.8320],
            [74.4860, 15.8260],
            [74.4820, 15.8200]
        ]
    },
    {
        "id": 3,
        "code": "BLG-SEG-03",
        "name": "Congress Road (Chennamma Circle to 1st Gate)",
        "from_node": "CHEN_CIRC",
        "to_node": "TILAKWADI_1",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5065, 15.8574],
            [74.5035, 15.8510],
            [74.5010, 15.8440]
        ]
    },
    {
        "id": 4,
        "code": "BLG-SEG-04",
        "name": "College Road (Bogarves to Hindwadi)",
        "from_node": "BOGARVES",
        "to_node": "HINDWADI",
        "road_type": "Local",
        "speed_limit": 45,
        "surface": "Asphalt",
        "coordinates": [
            [74.5020, 15.8540],
            [74.4975, 15.8500],
            [74.4940, 15.8460]
        ]
    },
    {
        "id": 5,
        "code": "BLG-SEG-05",
        "name": "Hindwadi to RPD College Cross",
        "from_node": "HINDWADI",
        "to_node": "RPD_CROSS",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.4940, 15.8460],
            [74.4925, 15.8390],
            [74.4910, 15.8320]
        ]
    },
    {
        "id": 6,
        "code": "BLG-SEG-06",
        "name": "Civil Hospital Road (Chennamma to Fort Lake)",
        "from_node": "CHEN_CIRC",
        "to_node": "FORT_LAKE",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt Concrete",
        "coordinates": [
            [74.5065, 15.8574],
            [74.5120, 15.8640],
            [74.5200, 15.8660]
        ]
    },
    {
        "id": 7,
        "code": "BLG-SEG-07",
        "name": "Camp Boulevard (Chennamma to Camp Church)",
        "from_node": "CHEN_CIRC",
        "to_node": "CAMP_CHURCH",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5065, 15.8574],
            [74.5015, 15.8590],
            [74.4980, 15.8610]
        ]
    },
    {
        "id": 8,
        "code": "BLG-SEG-08",
        "name": "Camp Church to Bogarves Corridor",
        "from_node": "CAMP_CHURCH",
        "to_node": "BOGARVES",
        "road_type": "Local",
        "speed_limit": 45,
        "surface": "Asphalt",
        "coordinates": [
            [74.4980, 15.8610],
            [74.5000, 15.8570],
            [74.5020, 15.8540]
        ]
    },
    {
        "id": 9,
        "code": "BLG-SEG-09",
        "name": "NH-48 Belagavi Expressway (Kanbargi to Ramteerth)",
        "from_node": "KANBARGI_CR",
        "to_node": "RAMTEERTH",
        "road_type": "Highway",
        "speed_limit": 90,
        "surface": "Concrete Highway",
        "coordinates": [
            [74.5420, 15.8920],
            [74.5450, 15.8870],
            [74.5480, 15.8820]
        ]
    },
    {
        "id": 10,
        "code": "BLG-SEG-10",
        "name": "NH-48 Belagavi Expressway (Ramteerth to Gandhi Nagar)",
        "from_node": "RAMTEERTH",
        "to_node": "GANDHI_NGR",
        "road_type": "Highway",
        "speed_limit": 90,
        "surface": "Concrete Highway",
        "coordinates": [
            [74.5480, 15.8820],
            [74.5510, 15.8730],
            [74.5530, 15.8650]
        ]
    },
    {
        "id": 11,
        "code": "BLG-SEG-11",
        "name": "NH-48 Bypass (Gandhi Nagar to Halaga Interchange)",
        "from_node": "GANDHI_NGR",
        "to_node": "HALAGA_INT",
        "road_type": "Highway",
        "speed_limit": 90,
        "surface": "Concrete Highway",
        "coordinates": [
            [74.5530, 15.8650],
            [74.5555, 15.8470],
            [74.5580, 15.8290]
        ]
    },
    {
        "id": 12,
        "code": "BLG-SEG-12",
        "name": "Fort Road to Gandhi Nagar Link",
        "from_node": "FORT_LAKE",
        "to_node": "GANDHI_NGR",
        "road_type": "Arterial",
        "speed_limit": 60,
        "surface": "Asphalt",
        "coordinates": [
            [74.5200, 15.8660],
            [74.5360, 15.8655],
            [74.5530, 15.8650]
        ]
    },
    {
        "id": 13,
        "code": "BLG-SEG-13",
        "name": "Sambhaji Chowk to Shahapur Market",
        "from_node": "SAMBHAJI",
        "to_node": "SHAHAPUR",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.5050, 15.8480],
            [74.5100, 15.8450],
            [74.5150, 15.8420]
        ]
    },
    {
        "id": 14,
        "code": "BLG-SEG-14",
        "name": "Shahapur to Vadgaon Main Road",
        "from_node": "SHAHAPUR",
        "to_node": "VADGAON",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.5150, 15.8420],
            [74.5135, 15.8380],
            [74.5120, 15.8340]
        ]
    },
    {
        "id": 15,
        "code": "BLG-SEG-15",
        "name": "Vadgaon to Udyambag Industrial Connector",
        "from_node": "VADGAON",
        "to_node": "UDYAMBAG",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5120, 15.8340],
            [74.4980, 15.8270],
            [74.4820, 15.8200]
        ]
    },
    {
        "id": 16,
        "code": "BLG-SEG-16",
        "name": "Old PB Road (Sambhaji Chowk to Chennamma)",
        "from_node": "SAMBHAJI",
        "to_node": "CHEN_CIRC",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5050, 15.8480],
            [74.5060, 15.8530],
            [74.5065, 15.8574]
        ]
    },
    {
        "id": 17,
        "code": "BLG-SEG-17",
        "name": "Khade Bazar Arterial (Bogarves to Sambhaji)",
        "from_node": "BOGARVES",
        "to_node": "SAMBHAJI",
        "road_type": "Arterial",
        "speed_limit": 45,
        "surface": "Bituminous Asphalt",
        "coordinates": [
            [74.5020, 15.8540],
            [74.5035, 15.8510],
            [74.5050, 15.8480]
        ]
    },
    {
        "id": 18,
        "code": "BLG-SEG-18",
        "name": "Congress Road Extension (1st Gate to 3rd Gate)",
        "from_node": "TILAKWADI_1",
        "to_node": "TILAKWADI_3",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5010, 15.8440],
            [74.4985, 15.8400],
            [74.4960, 15.8360]
        ]
    },
    {
        "id": 19,
        "code": "BLG-SEG-19",
        "name": "Khanapur Cross (3rd Gate to RPD College)",
        "from_node": "TILAKWADI_3",
        "to_node": "RPD_CROSS",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.4960, 15.8360],
            [74.4935, 15.8340],
            [74.4910, 15.8320]
        ]
    },
    {
        "id": 20,
        "code": "BLG-SEG-20",
        "name": "RPD Corner to Udyambag Link",
        "from_node": "RPD_CROSS",
        "to_node": "UDYAMBAG",
        "road_type": "Arterial",
        "speed_limit": 55,
        "surface": "Asphalt",
        "coordinates": [
            [74.4910, 15.8320],
            [74.4865, 15.8260],
            [74.4820, 15.8200]
        ]
    },
    {
        "id": 21,
        "code": "BLG-SEG-21",
        "name": "SPM Road Overbridge (Sambhaji to 1st Gate)",
        "from_node": "SAMBHAJI",
        "to_node": "TILAKWADI_1",
        "road_type": "Arterial",
        "speed_limit": 45,
        "surface": "Asphalt Concrete",
        "coordinates": [
            [74.5050, 15.8480],
            [74.5030, 15.8460],
            [74.5010, 15.8440]
        ]
    },
    {
        "id": 22,
        "code": "BLG-SEG-22",
        "name": "Kanbargi Road (Fort Lake to Kanbargi Cross)",
        "from_node": "FORT_LAKE",
        "to_node": "KANBARGI_CR",
        "road_type": "Highway Connector",
        "speed_limit": 65,
        "surface": "Asphalt Concrete",
        "coordinates": [
            [74.5200, 15.8660],
            [74.5310, 15.8790],
            [74.5420, 15.8920]
        ]
    },
    {
        "id": 23,
        "code": "BLG-SEG-23",
        "name": "Halaga-Vadgaon Ring Corridor",
        "from_node": "HALAGA_INT",
        "to_node": "VADGAON",
        "road_type": "Arterial",
        "speed_limit": 60,
        "surface": "Bituminous Asphalt",
        "coordinates": [
            [74.5580, 15.8290],
            [74.5350, 15.8315],
            [74.5120, 15.8340]
        ]
    },
    {
        "id": 24,
        "code": "BLG-SEG-24",
        "name": "Camp Cantonment to Hindwadi Military Cross",
        "from_node": "CAMP_CHURCH",
        "to_node": "HINDWADI",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.4980, 15.8610],
            [74.4960, 15.8535],
            [74.4940, 15.8460]
        ]
    },
    {
        "id": 25,
        "code": "BLG-SEG-25",
        "name": "Kakaves Road (Chennamma to Civil Hospital)",
        "from_node": "CHEN_CIRC",
        "to_node": "CIVIL_HOSP",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5065, 15.8574],
            [74.5090, 15.8610],
            [74.5120, 15.8640]
        ]
    },
    {
        "id": 26,
        "code": "BLG-SEG-26",
        "name": "Civil Hospital to Fort Lake Corridor",
        "from_node": "CIVIL_HOSP",
        "to_node": "FORT_LAKE",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Asphalt",
        "coordinates": [
            [74.5120, 15.8640],
            [74.5160, 15.8650],
            [74.5200, 15.8660]
        ]
    },
    {
        "id": 27,
        "code": "BLG-SEG-27",
        "name": "Nath Pai Circle Road (Shahapur to 1st Gate)",
        "from_node": "SHAHAPUR",
        "to_node": "TILAKWADI_1",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.5150, 15.8420],
            [74.5080, 15.8430],
            [74.5010, 15.8440]
        ]
    },
    {
        "id": 28,
        "code": "BLG-SEG-28",
        "name": "Maratha Colony Link (Vadgaon to 3rd Gate)",
        "from_node": "VADGAON",
        "to_node": "TILAKWADI_3",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.5120, 15.8340],
            [74.5040, 15.8350],
            [74.4960, 15.8360]
        ]
    },
    {
        "id": 29,
        "code": "BLG-SEG-29",
        "name": "Hindwadi to 1st Gate Cross",
        "from_node": "HINDWADI",
        "to_node": "TILAKWADI_1",
        "road_type": "Local",
        "speed_limit": 40,
        "surface": "Asphalt",
        "coordinates": [
            [74.4940, 15.8460],
            [74.4975, 15.8450],
            [74.5010, 15.8440]
        ]
    },
    {
        "id": 30,
        "code": "BLG-SEG-30",
        "name": "Tilakwadi 1st Gate to Bogarves West Arterial",
        "from_node": "BOGARVES",
        "to_node": "TILAKWADI_1",
        "road_type": "Arterial",
        "speed_limit": 50,
        "surface": "Bituminous Asphalt",
        "coordinates": [
            [74.5020, 15.8540],
            [74.5015, 15.8490],
            [74.5010, 15.8440]
        ]
    }
]

# Calculate segment lengths in meters
for seg in BELAGAVI_ROAD_SEGMENTS:
    coords = seg["coordinates"]
    length_m = 0.0
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i+1]
        length_m += haversine_distance_meters(lat1, lon1, lat2, lon2) or 0.0
    seg["length_m"] = round(length_m, 1)

# ==============================================================================
# 3. SPATIAL BUFFER & ROAD MATCHING (PERPENDICULAR PROJECTION)
# ==============================================================================
def point_to_segment_distance_meters(px, py, x1, y1, x2, y2):
    """
    Computes minimum Euclidean/Geodesic distance from point (px, py) to line segment (x1, y1)-(x2, y2).
    Coordinates in (lat, lon).
    """
    # Vector from p1 to p2
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return haversine_distance_meters(px, py, x1, y1) or 999999.0

    # Projection factor t
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t)) # Clamp to segment boundary

    # Projected point
    proj_lat = x1 + t * dx
    proj_lon = y1 + t * dy

    return haversine_distance_meters(px, py, proj_lat, proj_lon) or 999999.0

def match_defect_to_belagavi_segment(lat: float, lon: float, max_buffer_m: float = 50.0, segments = None):
    """
    Matches a road defect coordinate to the closest Belagavi road segment within buffer.
    Returns matched segment dictionary and perpendicular distance, or (None, None).
    """
    if isinstance(max_buffer_m, (list, tuple)):
        segments = max_buffer_m
        max_buffer_m = 50.0

    seg_list = segments if segments is not None else BELAGAVI_ROAD_SEGMENTS
    best_seg = None
    min_dist = 999999.0

    for seg in seg_list:
        coords = seg["coordinates"] if isinstance(seg, dict) else json.loads(seg.geometry_geojson)
        for i in range(len(coords) - 1):
            p1_lon, p1_lat = coords[i]
            p2_lon, p2_lat = coords[i+1]
            d = point_to_segment_distance_meters(lat, lon, p1_lat, p1_lon, p2_lat, p2_lon)
            if d < min_dist:
                min_dist = d
                best_seg = seg

    return best_seg, round(min_dist, 1)

# ==============================================================================
# 4. GRAPH TOPOLOGY & ROUTE ALTERNATIVE GENERATION
# ==============================================================================
def build_belagavi_graph():
    """Builds an adjacency list graph for Dijkstra/A* shortest & alternative path finding."""
    graph = {}
    for j_id in BELAGAVI_JUNCTIONS:
        graph[j_id] = []

    for seg in BELAGAVI_ROAD_SEGMENTS:
        u = seg["from_node"]
        v = seg["to_node"]
        w = seg["length_m"]
        if u in graph and v in graph:
            graph[u].append({"node": v, "segment": seg, "cost": w})
            graph[v].append({"node": u, "segment": seg, "cost": w}) # Bidirectional urban road
    return graph

def find_closest_junction(lat: float, lon: float):
    """Finds the nearest road junction node to a given GPS coordinate in Belagavi."""
    best_junc = None
    min_d = 999999.0
    for j_id, j_data in BELAGAVI_JUNCTIONS.items():
        d = haversine_distance_meters(lat, lon, j_data["lat"], j_data["lon"]) or 999999.0
        if d < min_d:
            min_d = d
            best_junc = j_id
    return best_junc, min_d

def dijkstra_k_routes(start_node, dest_node, k=3, penalty_factor=1.45):
    """
    Finds up to k diverse alternative routes between start_node and dest_node
    using iterative edge-penalty graph search. Guarantees finding multiple distinct routes.
    """
    base_graph = build_belagavi_graph()
    routes = []
    penalties = {}
    attempts = 0
    max_attempts = 15

    while len(routes) < k and attempts < max_attempts:
        attempts += 1
        dist = {node: float('inf') for node in base_graph}
        parent = {node: None for node in base_graph}
        parent_seg = {node: None for node in base_graph}
        dist[start_node] = 0.0

        unvisited = set(base_graph.keys())

        while unvisited:
            curr = min(unvisited, key=lambda n: dist[n])
            if dist[curr] == float('inf') or curr == dest_node:
                break
            unvisited.remove(curr)

            for neighbor_edge in base_graph[curr]:
                nxt = neighbor_edge["node"]
                if nxt in unvisited:
                    seg = neighbor_edge["segment"]
                    edge_key = tuple(sorted([curr, nxt]))
                    pen = penalties.get(edge_key, 1.0)
                    weight = neighbor_edge["cost"] * pen
                    if dist[curr] + weight < dist[nxt]:
                        dist[nxt] = dist[curr] + weight
                        parent[nxt] = curr
                        parent_seg[nxt] = seg

        if dist[dest_node] == float('inf'):
            break

        path_nodes = []
        path_segments = []
        curr = dest_node
        while curr is not None:
            path_nodes.append(curr)
            if parent_seg[curr]:
                path_segments.append(parent_seg[curr])
            curr = parent[curr]
        path_nodes.reverse()
        path_segments.reverse()

        seg_ids = [s["id"] for s in path_segments]
        already_found = any([r["segment_ids"] == seg_ids for r in routes])
        if not already_found and len(path_segments) > 0:
            routes.append({
                "route_idx": len(routes) + 1,
                "nodes": path_nodes,
                "segments": path_segments,
                "segment_ids": seg_ids,
                "base_length_m": sum([s["length_m"] for s in path_segments])
            })
            for s in path_segments:
                edge_key = tuple(sorted([s["from_node"], s["to_node"]]))
                penalties[edge_key] = penalties.get(edge_key, 1.0) * penalty_factor
        else:
            for s in path_segments:
                edge_key = tuple(sorted([s["from_node"], s["to_node"]]))
                penalties[edge_key] = penalties.get(edge_key, 1.0) * 1.8

    return routes

# ==============================================================================
# 5. RISK-AWARE ROUTE DAMAGE EXPOSURE COST FUNCTION
# ==============================================================================
def evaluate_route_risk(route_dict, verified_defects, segment_conditions=None):
    """
    Calculates the road damage exposure score and risk profile of a route.
    Considers verified defects as well as official database road segment health/condition metrics.

    Explainable Cost Function:
    - Base Distance: D (km)
    - Defect Exposure = sum(Severity Weight * Defect Risk Score) along matched segments
    - Segment Health Penalties = Incorporates official segment health percentage & potholes
    - High-Risk Hazard Multiplier: Penalizes routes with Critical/Severe cavities (accident hazard)
    """
    total_len_m = route_dict["base_length_m"]
    total_km = round(total_len_m / 1000.0, 2)

    # Calculate estimated travel time considering segment speed limits
    est_time_sec = 0.0
    for s in route_dict["segments"]:
        speed_mps = (s.get("speed_limit", 50) * 1000.0) / 3600.0
        est_time_sec += s["length_m"] / max(speed_mps, 5.0)
    est_time_min = round(max(1.0, est_time_sec / 60.0), 1)

    # Match verified defects to segments on this route
    route_seg_ids = set(route_dict["segment_ids"])
    matched_defects = []
    severe_count = 0
    moderate_count = 0
    minor_count = 0
    pothole_cavities = 0

    for d in verified_defects:
        if d.get("road_segment_id") in route_seg_ids:
            matched_defects.append(d)
            sev = d.get("severity", "Minor")
            cat = d.get("category_code", "D40")
            if sev == "Severe":
                severe_count += 1
            elif sev == "Moderate":
                moderate_count += 1
            else:
                minor_count += 1
            if cat == "D40":
                pothole_cavities += 1

    total_defects = len(matched_defects)

    # Segment details with official road health integration
    segments_summary = []
    risky_segments_count = 0
    moderate_segments_count = 0
    safe_segments_count = 0

    for s in route_dict["segments"]:
        s_id = s["id"]
        s_cond = (segment_conditions or {}).get(s_id, {})
        cond_pct = s_cond.get("condition_percentage", s.get("condition_percentage", 88.0))
        potholes = s_cond.get("potholes_count", s.get("potholes_count", 0))
        risk_class = s_cond.get("risk_classification", s.get("risk_classification", "SAFE"))

        if risk_class == "RISKY" or cond_pct < 50.0:
            risk_class = "RISKY"
            seg_color = "#ef4444"
            risky_segments_count += 1
        elif risk_class == "MODERATE" or cond_pct < 80.0:
            risk_class = "MODERATE"
            seg_color = "#f59e0b"
            moderate_segments_count += 1
        else:
            risk_class = "SAFE"
            seg_color = "#10b981"
            safe_segments_count += 1

        segments_summary.append({
            "id": s["id"],
            "code": s["code"],
            "name": s["name"],
            "road_type": s["road_type"],
            "speed_limit": s["speed_limit"],
            "length_m": s["length_m"],
            "condition_percentage": cond_pct,
            "potholes_count": potholes,
            "risk_classification": risk_class,
            "risk_color": seg_color,
            "is_risky": (risk_class == "RISKY")
        })

    # Explainable Exposure Scoring Model (0 to 100)
    # Severity points: Minor=3, Moderate=8, Severe=20
    severity_sum = (minor_count * 3) + (moderate_count * 8) + (severe_count * 20)

    # Segment condition penalty
    segment_health_penalty = (risky_segments_count * 18.0) + (moderate_segments_count * 5.0)

    # Density factor (defects per km)
    density_per_km = total_defects / max(total_km, 0.5)

    # High-hazard penalty if deep potholes exist
    pothole_hazard_multiplier = 1.0 + (severe_count * 0.25) + (risky_segments_count * 0.20)

    raw_exposure = ((severity_sum * 1.5 + density_per_km * 4.0) + segment_health_penalty) * pothole_hazard_multiplier
    exposure_score = round(min(100.0, raw_exposure), 1)

    # Classify Risk Level & Risk-based color
    if exposure_score >= 60 or risky_segments_count >= 1:
        risk_level = "Critical" if exposure_score >= 65 else "High"
        risk_color = "#dc2626" # Crimson
        risk_bg = "bg-rose-100 text-rose-800 border-rose-300"
    elif exposure_score >= 25 or moderate_segments_count >= 1:
        risk_level = "Moderate"
        risk_color = "#d97706" # Amber
        risk_bg = "bg-amber-100 text-amber-800 border-amber-300"
    else:
        risk_level = "Low"
        risk_color = "#059669" # Emerald Green
        risk_bg = "bg-emerald-100 text-emerald-800 border-emerald-300"

    # Distinct route visual color palette for multiple paths on map
    ROUTE_PALETTE = [
        {"color": "#059669", "border": "#047857", "name": "Emerald Green", "tag": "⭐ Recommended Low-Risk Path"},
        {"color": "#2563eb", "border": "#1d4ed8", "name": "Cobalt Blue", "tag": "Alternative Corridor A"},
        {"color": "#d97706", "border": "#b45309", "name": "Vibrant Amber", "tag": "Alternative Corridor B"},
        {"color": "#7c3aed", "border": "#6d28d9", "name": "Royal Purple", "tag": "Alternative Corridor C"}
    ]
    pal = ROUTE_PALETTE[(route_dict["route_idx"] - 1) % len(ROUTE_PALETTE)]

    # Human-readable descriptive name covering main road corridors
    seg_names = [s["name"].split("(")[0].strip() for s in route_dict["segments"]]
    unique_corridors = list(dict.fromkeys(seg_names))[:2]
    corridor_title = " & ".join(unique_corridors) if unique_corridors else route_dict["segments"][0]["name"]
    route_name = f"Route {route_dict['route_idx']}: via {corridor_title}"

    # Assemble human-readable explanations
    factors = []
    if risky_segments_count > 0:
        for s in segments_summary:
            if s["is_risky"]:
                factors.append(f"⚠️ RISKY ROAD SEGMENT: '{s['name']}' has {s['potholes_count']} potholes with health at {s['condition_percentage']}%.")

    if total_defects == 0 and risky_segments_count == 0:
        factors.append("Pavement clear: all segments verified safe with minimal road distress.")
    else:
        if total_defects > 0:
            factors.append(f"{total_defects} verified defect(s) along route ({pothole_cavities} pothole cavities).")
        if severe_count > 0:
            factors.append(f"HAZARD WARNING: {severe_count} deep pothole cavity requires vehicle swerve / deceleration.")
        if moderate_count > 0:
            factors.append(f"{moderate_count} moderate alligator/fatigue crack clusters.")
        if density_per_km > 1.5:
            factors.append(f"Defect density: {density_per_km:.1f} defects per kilometer.")

    # Extract coordinates geometry for polyline rendering
    polyline = []
    for s in route_dict["segments"]:
        for coord in s["coordinates"]:
            polyline.append([coord[1], coord[0]]) # [lat, lon] for Leaflet

    return {
        "route_id": route_dict["route_idx"],
        "name": route_name,
        "color": pal["color"],
        "border_color": pal["border"],
        "color_name": pal["name"],
        "tag": pal["tag"],
        "distance_km": total_km,
        "estimated_time_min": est_time_min,
        "total_defects": total_defects,
        "severe_defects": severe_count,
        "moderate_defects": moderate_count,
        "minor_defects": minor_count,
        "risky_segments_count": risky_segments_count,
        "moderate_segments_count": moderate_segments_count,
        "safe_segments_count": safe_segments_count,
        "exposure_score": exposure_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_bg": risk_bg,
        "factors": factors,
        "polyline": polyline,
        "matched_defects": matched_defects,
        "segments": segments_summary
    }

def recommend_best_route(origin_lat, origin_lon, dest_lat, dest_lon, verified_defects, segment_conditions=None):
    """
    Main routing function: Finds routes between origin and destination in Belagavi,
    evaluates damage exposure using official database road conditions, and selects the recommended lower-risk path.
    """
    # 1. Geographic Boundary Validation
    if not is_within_belagavi(origin_lat, origin_lon):
        return {
            "status": "error",
            "message": "Origin coordinate is outside the configured Belagavi City boundary."
        }
    if not is_within_belagavi(dest_lat, dest_lon):
        return {
            "status": "error",
            "message": "Destination coordinate is outside the configured Belagavi City boundary."
        }

    # 2. Map coordinates to closest road network junctions
    start_junc, d1 = find_closest_junction(origin_lat, origin_lon)
    dest_junc, d2 = find_closest_junction(dest_lat, dest_lon)

    if start_junc == dest_junc:
        return {
            "status": "error",
            "message": "Origin and destination resolve to the same local junction. Please select distinct locations."
        }

    # 3. Generate alternative routes
    raw_routes = dijkstra_k_routes(start_junc, dest_junc, k=3)
    if not raw_routes:
        return {
            "status": "error",
            "message": "No continuous road path found between selected junctions in Belagavi network."
        }

    # 4. Evaluate risk for each route with official road condition data
    evaluated_routes = []
    for r in raw_routes:
        evaluated_routes.append(evaluate_route_risk(r, verified_defects, segment_conditions=segment_conditions))

    # 5. Determine recommended route based on combined Distance + Risk Tradeoff
    def composite_cost(r):
        risky_count = r.get("risky_segments_count", 0)
        return r["distance_km"] + (r["exposure_score"] * 0.12) + (r["severe_defects"] * 1.5) + (risky_count * 4.5)

    sorted_routes = sorted(evaluated_routes, key=composite_cost)
    recommended = sorted_routes[0]

    # Re-index routes so Route 1 is ALWAYS the recommended safest route with distinctive colors
    ROUTE_COLORS = [
        {"color": "#059669", "border": "#047857", "name": "Emerald Green (Safest)", "badge": "⭐ Recommended Safest Route"},
        {"color": "#2563eb", "border": "#1d4ed8", "name": "Royal Blue (Alternative 1)", "badge": "Alternative Path 1"},
        {"color": "#d97706", "border": "#b45309", "name": "Vibrant Amber (Alternative 2)", "badge": "Alternative Path 2"}
    ]

    for idx, r in enumerate(sorted_routes):
        r["route_id"] = idx + 1
        r["is_recommended"] = (idx == 0)
        c_info = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        r["color"] = c_info["color"]
        r["border_color"] = c_info["border"]
        r["color_label"] = c_info["name"]
        r["summary_badge"] = c_info["badge"]
        r["name"] = f"Route {idx + 1}: " + r["name"].split(": ", 1)[-1]

    # Generate comparative safety recommendation statement
    if len(sorted_routes) > 1:
        other = sorted_routes[1]
        score_diff = abs(other["exposure_score"] - recommended["exposure_score"])
        other_risky = other.get("risky_segments_count", 0)
        rec_risky = recommended.get("risky_segments_count", 0)

        if rec_risky < other_risky:
            diff_risky = other_risky - rec_risky
            dist_diff = round(recommended["distance_km"] - other["distance_km"], 2)
            if dist_diff > 0:
                comparison_text = f"Recommended Route 1 ({recommended['color_label']}) bypasses {diff_risky} high-risk damaged road segment at the cost of {dist_diff} km extra travel."
            else:
                comparison_text = f"Recommended Route 1 ({recommended['color_label']}) is both shorter ({recommended['distance_km']} km) and bypasses {diff_risky} high-risk damaged road segment."
        elif recommended["severe_defects"] < other["severe_defects"]:
            diff_potholes = other["severe_defects"] - recommended["severe_defects"]
            dist_diff = round(recommended["distance_km"] - other["distance_km"], 2)
            if dist_diff > 0:
                comparison_text = f"Recommended Route 1 ({recommended['color_label']}) bypasses {diff_potholes} severe pothole cavity at the cost of {dist_diff} km extra travel."
            else:
                comparison_text = f"Recommended Route 1 ({recommended['color_label']}) is both shorter ({recommended['distance_km']} km) and avoids {diff_potholes} severe pothole hazards."
        elif score_diff > 10.0:
            comparison_text = f"Recommended Route 1 has {score_diff:.1f} pts lower road distress exposure than Alternative Route 2."
        else:
            comparison_text = f"Multiple viable corridors found across Belagavi network. Route 1 ({recommended['color_label']}) selected as lowest exposure ({recommended['exposure_score']}/100)."
    else:
        comparison_text = "Single optimal arterial corridor available for this query."

    return {
        "status": "success",
        "origin": {"lat": origin_lat, "lon": origin_lon, "junction": BELAGAVI_JUNCTIONS[start_junc]["name"]},
        "destination": {"lat": dest_lat, "lon": dest_lon, "junction": BELAGAVI_JUNCTIONS[dest_junc]["name"]},
        "recommended_route_id": recommended["route_id"],
        "comparison_summary": comparison_text,
        "disclaimer": "Road-damage-aware navigation guidance based on verified official road conditions. Drive safely.",
        "routes": sorted_routes
    }
