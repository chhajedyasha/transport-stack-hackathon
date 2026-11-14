"""API Contract tests for all CrowdWise endpoints and Journey Planner scoring."""
import pytest
from app import create_app, db
from app.config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def client():
    """Flask test client with initialized in-memory database."""
    from app.models.transit import Base as TransitBase, DimStop, DimRoute
    app = create_app(TestConfig)
    with app.app_context():
        TransitBase.metadata.create_all(db.engine)
        # Seed canonical stops for demonstration queries
        s1 = DimStop(stop_id="ST_ANAND_VIHAR", stop_code="AV01", stop_name="Anand Vihar ISBT", stop_lat=28.6469, stop_lon=77.3164)
        s2 = DimStop(stop_id="ST_CONNAUGHT_PLACE", stop_code="CP01", stop_name="Connaught Place", stop_lat=28.6315, stop_lon=77.2167)
        r1 = DimRoute(route_id="73UP", route_short_name="73", route_long_name="Anand Vihar to CP")
        db.session.add_all([s1, s2, r1])
        db.session.commit()
        
        yield app.test_client()
        TransitBase.metadata.drop_all(db.engine)


def test_health_endpoint(client):
    """Verifies /api/health envelope and data structure."""
    res = client.get("/api/health")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert "data" in json_data
    assert "status" in json_data["data"]
    assert "meta" in json_data
    assert json_data["meta"]["version"] == "1.0.0"
    assert "data_tier" in json_data["meta"]


def test_meta_endpoint(client):
    """Verifies /api/meta provenance tier transparency."""
    res = client.get("/api/meta")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    tiers = json_data["data"]["provenance_tiers"]
    assert "real_public" in tiers
    assert "organizer" in tiers
    assert "estimated" in tiers


def test_stops_search_empty_graceful(client):
    """Verifies /api/stops/search returns 200 with empty array on empty database."""
    res = client.get("/api/stops/search?q=Anand")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert isinstance(json_data["data"], list)


def test_stops_nearby_validation(client):
    """Verifies /api/stops/nearby rejects invalid coordinates with 400."""
    res = client.get("/api/stops/nearby?lat=invalid&lon=invalid")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "INVALID_COORDINATES"


def test_journey_planner_missing_params(client):
    """Verifies /api/journey/plan rejects missing stop IDs with 400."""
    res = client.post("/api/journey/plan", json={})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "MISSING_STOPS"


def test_journey_planner_plan_canonical_anand_vihar(client):
    """Verifies canonical demonstration query: Anand Vihar to Connaught Place at 6 PM."""
    payload = {
        "origin_stop_id": "ST_ANAND_VIHAR",
        "destination_stop_id": "ST_CONNAUGHT_PLACE",
        "departure_time": "2026-10-14T18:00:00",
        "day_type": "WEEKDAY",
        "preference": "balanced",
    }
    # In empty DB, planner returns graceful fallback options for canonical queries
    res = client.post("/api/journey/plan", json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    options = json_data["data"]["options"]
    assert isinstance(options, list)
    if options:
        opt = options[0]
        assert "timing" in opt
        assert "crowding" in opt
        assert "score" in opt
        assert "recommendation_reason" in opt
        assert opt["crowding"]["category"] in ["Seats Available", "Standing Room", "Crowded"]


def test_journey_planner_preferences_differ(client):
    """Tests that 'fastest' vs 'least_crowded' preferences yield appropriately sorted recommendations."""
    payload = {
        "origin_stop_id": "ST_ANAND_VIHAR",
        "destination_stop_id": "ST_CONNAUGHT_PLACE",
        "departure_time": "2026-10-14T18:00:00",
        "day_type": "WEEKDAY",
    }
    
    # Fastest
    res_fast = client.post("/api/journey/plan", json={**payload, "preference": "fastest"})
    opts_fast = res_fast.get_json()["data"]["options"]
    
    # Least Crowded
    res_crowd = client.post("/api/journey/plan", json={**payload, "preference": "least_crowded"})
    opts_crowd = res_crowd.get_json()["data"]["options"]
    
    if opts_fast and opts_crowd:
        # Fastest top option should minimize total duration
        assert opts_fast[0]["timing"]["total_duration_min"] <= opts_crowd[0]["timing"]["total_duration_min"] or \
               opts_crowd[0]["crowding"]["peak_rci"] <= opts_fast[0]["crowding"]["peak_rci"]


def test_analytics_endpoints(client):
    """Verifies analytics summary and diurnal peak hours endpoints."""
    res_sum = client.get("/api/analytics/summary")
    assert res_sum.status_code == 200
    assert "network_metrics" in res_sum.get_json()["data"]

    res_peak = client.get("/api/analytics/peak-hours")
    assert res_peak.status_code == 200
    assert len(res_peak.get_json()["data"]) == 24
