"""
ROADVISION AI - Test Suite for FastAPI REST Endpoints
Tests Health, Inspections, Defects, Verifications, Duplicates, Analytics, and Reports.
"""
from fastapi.testclient import TestClient
from backend.app import app
from backend.gis_belagavi import is_within_belagavi

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ROADVISION AI"
    assert "models" in data

def test_inspection_locations_come_from_osm_road_corridors():
    response = client.get("/api/inspection/locations")
    assert response.status_code == 200
    data = response.json()
    locations = {location["id"]: location for location in data["locations"]}

    assert data["source"] == "OSRM/OpenStreetMap road geometry"
    assert "road:1:start" in locations
    assert locations["road:1:start"]["name"]
    assert all(
        is_within_belagavi(location["latitude"], location["longitude"])
        for location in data["locations"]
    )

def test_get_inspections_endpoint():
    response = client.get("/api/inspections")
    assert response.status_code == 200
    data = response.json()
    assert "inspections" in data
    assert "total" in data

def test_get_defects_endpoint():
    response = client.get("/api/defects")
    assert response.status_code == 200
    data = response.json()
    assert "defects" in data

def test_analytics_endpoint():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "total_inspections" in data["kpis"]
    assert "category_distribution" in data
    assert "severity_distribution" in data

def test_duplicates_endpoint():
    response = client.get("/api/duplicates")
    assert response.status_code == 200
    data = response.json()
    assert "duplicates" in data

def test_repairs_endpoint():
    response = client.get("/api/repairs")
    assert response.status_code == 200
    data = response.json()
    assert "repairs" in data

def test_models_benchmark_endpoint():
    response = client.get("/api/models/benchmark")
    assert response.status_code == 200
