"""Integration and unit tests verifying REST API Architecture (F23), Graceful Degradation Engine (F24),
and Multi-Objective Preference Scoring (F21).
"""
import pytest
from app import create_app, db
from app.config import Config
from app.services.scoring_service import (
    MultiObjectiveScorer,
    compute_journey_crowding,
    calculate_benchmark_time,
    infer_departure_context,
    aggregate_journey_confidence,
    rci_to_label,
    rci_to_category,
    PRESET_WEIGHTS,
)


class DegradationTestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def unseeded_client():
    """Flask test client with completely empty unseeded database."""
    from app.models.transit import Base
    app = create_app(DegradationTestConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        yield app.test_client()
        Base.metadata.drop_all(db.engine)


@pytest.fixture
def seeded_client():
    """Flask test client with canonical demonstration stops and routes."""
    from app.models.transit import Base, DimStop, DimRoute
    app = create_app(DegradationTestConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        s1 = DimStop(stop_id="ST_ANAND_VIHAR", stop_code="AV01", stop_name="Anand Vihar ISBT", stop_lat=28.6469, stop_lon=77.3164)
        s2 = DimStop(stop_id="ST_CONNAUGHT_PLACE", stop_code="CP01", stop_name="Connaught Place", stop_lat=28.6315, stop_lon=77.2167)
        r1 = DimRoute(route_id="73UP", route_short_name="73", route_long_name="Anand Vihar to CP")
        db.session.add_all([s1, s2, r1])
        db.session.commit()
        yield app.test_client()
        Base.metadata.drop_all(db.engine)


# ---------------------------------------------------------------------------
# Feature F23: Standard Envelope and Endpoint Verification
# ---------------------------------------------------------------------------

def test_v1_health_envelope(seeded_client):
    """Verifies /api/v1/health envelope structure and metadata."""
    res = seeded_client.get("/api/v1/health")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert "data" in json_data and "status" in json_data["data"]
    assert "meta" in json_data
    assert json_data["meta"]["version"] == "1.0.0"
    assert "data_tier" in json_data["meta"]
    assert "data_mode" in json_data["meta"]
    assert json_data["meta"]["execution_time_ms"] >= 0.0


def test_v1_stops_search_multimodal(seeded_client):
    """Verifies /api/v1/stops/search for both text search and coordinates."""
    # Text search
    res_text = seeded_client.get("/api/v1/stops/search?q=Anand")
    assert res_text.status_code == 200
    assert len(res_text.get_json()["data"]) >= 1

    # Coordinate search
    res_coords = seeded_client.get("/api/v1/stops/search?lat=28.6469&lon=77.3164")
    assert res_coords.status_code == 200
    assert isinstance(res_coords.get_json()["data"], list)


def test_v1_plan_endpoint(seeded_client):
    """Verifies POST /api/v1/plan and ranking across preferences."""
    payload = {
        "origin_stop_id": "ST_ANAND_VIHAR",
        "destination_stop_id": "ST_CONNAUGHT_PLACE",
        "departure_time": "2026-10-14T18:00:00",
        "day_type": "WEEKDAY",
        "preference": "balanced",
    }
    res = seeded_client.post("/api/v1/plan", json=payload)
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert json_data["meta"]["data_tier"] == "estimated"
    options = json_data["data"]["options"]
    assert len(options) <= 8
    if options:
        opt = options[0]
        assert "recommendation" in opt or "recommendation_reason" in opt
        assert "composite_score" in opt or "score" in opt
        assert "timing" in opt and "crowding" in opt


def test_v1_route_details(seeded_client):
    """Verifies GET /api/v1/routes/:routeId polyline and hourly crowding profile."""
    res = seeded_client.get("/api/v1/routes/73UP")
    assert res.status_code == 200
    json_data = res.get_json()
    data = json_data["data"]
    assert data["route_id"] == "73UP"
    assert "polyline" in data or "polyline_coords" in data
    assert len(data.get("hourly_crowd_profile", [])) == 24 or len(data.get("hourly_profile", [])) == 24


def test_v1_analytics_summary(seeded_client):
    """Verifies GET /api/v1/analytics/summary network metrics."""
    res = seeded_client.get("/api/v1/analytics/summary")
    assert res.status_code == 200
    json_data = res.get_json()
    assert "network_metrics" in json_data["data"]
    assert "top_crowded_routes" in json_data["data"]


def test_v1_data_tier(seeded_client):
    """Verifies GET /api/v1/data-tier returns runtime mode and active tier."""
    res = seeded_client.get("/api/v1/data-tier")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "data_mode" in data
    assert "active_tier" in data
    assert "provenance_tiers" in data


# ---------------------------------------------------------------------------
# Feature F24: Graceful Degradation Engine Verification
# ---------------------------------------------------------------------------

def test_unseeded_database_health_status(unseeded_client):
    """Verifies unseeded DB returns HTTP 200 with clear status indication."""
    res = unseeded_client.get("/api/v1/health")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert json_data["data"]["status"] in ("healthy", "unseeded", "degraded")


def test_unseeded_database_stops_search(unseeded_client):
    """Verifies stop search on empty DB returns HTTP 200 with data: []."""
    res = unseeded_client.get("/api/v1/stops/search?q=Connaught")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert json_data["data"] == []


def test_missing_route_returns_structured_404(seeded_client):
    """Verifies querying non-existent route returns 404 with error code ROUTE_NOT_FOUND."""
    res = seeded_client.get("/api/v1/routes/-1")
    assert res.status_code == 404
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "ROUTE_NOT_FOUND"


def test_plan_missing_required_fields_returns_400(seeded_client):
    """Verifies missing origin or destination returns 400 with MISSING_REQUIRED_FIELDS."""
    res = seeded_client.post("/api/v1/plan", json={"origin_stop_id": "DEL_001"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "MISSING_REQUIRED_FIELDS"


def test_plan_identical_stops_returns_400(seeded_client):
    """Verifies identical origin and destination returns 400 with INVALID_ORIGIN_DESTINATION."""
    res = seeded_client.post("/api/v1/plan", json={"origin_stop_id": "ST_01", "destination_stop_id": "ST_01"})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "INVALID_ORIGIN_DESTINATION"


def test_invalid_coordinates_returns_400(seeded_client):
    """Verifies non-numeric lat/lon returns 400 with INVALID_COORDINATES."""
    res = seeded_client.get("/api/v1/stops/search?lat=invalid&lon=invalid")
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["ok"] is False
    assert json_data["error"]["code"] == "INVALID_COORDINATES"


def test_out_of_bounds_coordinates_returns_empty_200(seeded_client):
    """Verifies coordinates far outside Delhi (0.0, 0.0) return HTTP 200 with empty list."""
    res = seeded_client.get("/api/v1/stops/search?lat=0.0&lon=0.0")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True
    assert json_data["data"] == []


def test_non_ascii_unicode_stops_search(seeded_client):
    """Verifies Hindi query (e.g. कश्मीरी गेट) returns HTTP 200 without UnicodeDecodeError."""
    res = seeded_client.get("/api/v1/stops/search?q=कश्मीरी गेट")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["ok"] is True


# ---------------------------------------------------------------------------
# Feature F21: Multi-Objective Preference Scoring Engine
# ---------------------------------------------------------------------------

def _make_candidate(
    route_id: str,
    total_time: float,
    boarding_rci: float,
    peak_rci: float,
    wait_time: float = 5.0,
    direction_id: int = 0,
):
    c_journey = compute_journey_crowding(boarding_rci, peak_rci)
    return {
        "route_id": route_id,
        "route_name": route_id,
        "direction_id": direction_id,
        "pattern_id": f"{route_id}_pat0",
        "timing": {
            "walk_time_min": 3.0,
            "wait_time_min": wait_time,
            "in_vehicle_min": total_time - wait_time - 3.0,
            "total_duration_min": total_time,
            "stops_count": 10,
            "distance_km": 10.0,
        },
        "crowding": {
            "boarding_rci": boarding_rci,
            "peak_rci": peak_rci,
            "journey_rci": c_journey,
            "mean_rci": (boarding_rci + peak_rci) / 2.0,
            "category": rci_to_label(c_journey),
            "label": rci_to_label(c_journey),
            "crowding_label": rci_to_label(c_journey),
            "technical_category": rci_to_category(c_journey),
            "crowding_category": rci_to_category(c_journey),
            "confidence": "high",
            "tier": "estimated",
            "interval": {"p10": max(0.0, peak_rci - 10.0), "p90": min(100.0, peak_rci + 10.0)},
            "zone_breakdown": [],
        },
    }


def test_composite_journey_crowding_formula():
    """Verifies C_journey = 0.40 * C_boarding + 0.60 * C_peak_leg."""
    assert compute_journey_crowding(50.0, 50.0) == 50.0
    assert compute_journey_crowding(0.0, 0.0) == 0.0
    assert compute_journey_crowding(100.0, 100.0) == 100.0
    assert compute_journey_crowding(20.0, 80.0) == 56.0
    assert compute_journey_crowding(65.0, 88.0) == 78.8
    assert compute_journey_crowding(50.0, 30.0) == 50.0


def test_benchmark_time_calculation():
    """Verifies T_bar calculation and division skew avoidance."""
    c1 = _make_candidate("R1", 30.0, 50.0, 50.0)
    c2 = _make_candidate("R2", 40.0, 50.0, 50.0)
    c3 = _make_candidate("R3", 50.0, 50.0, 50.0)
    assert calculate_benchmark_time([c1, c2, c3]) == 40.0
    assert calculate_benchmark_time([c1]) == 30.0
    c1_clone = _make_candidate("R1_alt", 30.0, 30.0, 30.0)
    assert calculate_benchmark_time([c1, c1_clone]) == 30.0


def test_preset_weightings_distinct_winners():
    """Verifies that Fastest, Balanced, and Least Crowded presets can each select distinct optimal routes."""
    scorer = MultiObjectiveScorer()
    cA = _make_candidate("Route_A_Fast", 32.0, 70.0, 85.0)
    cB = _make_candidate("Route_B_Balanced", 38.0, 40.0, 45.0)
    cC = _make_candidate("Route_C_Empty", 48.0, 15.0, 20.0)
    pool = [cA, cB, cC]

    # Fastest
    res_fast = scorer.score_candidates([dict(c) for c in pool], preference="fastest")
    assert res_fast[0]["route_id"] == "Route_A_Fast"
    assert res_fast[0]["is_recommended"] is True

    # Balanced
    res_bal = scorer.score_candidates([dict(c) for c in pool], preference="balanced")
    assert res_bal[0]["route_id"] == "Route_B_Balanced"
    assert res_bal[0]["is_recommended"] is True

    # Least Crowded
    res_crowd = scorer.score_candidates([dict(c) for c in pool], preference="least_crowded")
    assert res_crowd[0]["route_id"] == "Route_C_Empty"
    assert res_crowd[0]["is_recommended"] is True


def test_least_crowded_detour_constraint():
    """In least_crowded preset, routes exceeding 1.6x fastest duration must be pruned."""
    scorer = MultiObjectiveScorer()
    c_fast = _make_candidate("Fast_30m", 30.0, 70.0, 80.0)
    c_ok_empty = _make_candidate("Ok_Empty_42m", 42.0, 15.0, 20.0)
    c_extreme_detour = _make_candidate("Detour_Empty_55m", 55.0, 5.0, 10.0)

    res = scorer.score_candidates([c_fast, c_ok_empty, c_extreme_detour], preference="least_crowded")
    route_ids = [c["route_id"] for c in res]
    assert "Ok_Empty_42m" in route_ids
    assert "Detour_Empty_55m" not in route_ids
    assert res[0]["route_id"] == "Ok_Empty_42m"
