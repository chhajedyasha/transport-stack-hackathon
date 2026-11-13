"""crowdwise/backend/tests/test_stop_search_adversarial.py
Adversarial and Empirical Stress Test Harness for Multi-Modal Stop Search (F05).
Empirically verifies:
1. Spatial cKDTree search latency SLA (<0.20ms) across 20,000 synthetic GPS points.
2. Handling of coordinates outside Delhi NCR boundary.
3. Vernacular transliteration recall (Kashmere Gate, Dhaula Kuan, AIIMS, etc.).
4. Adversarial input resilience: SQLi, XSS, control chars, whitespace, extremes.
5. Invariant preservation and database integrity.
"""
import math
import time
import pytest
import numpy as np
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.transit import (
    DimStop,
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimTripStart,
    FactRouteSupply,
)
from app.services.gtfs_service import load_all_stops
from app.services.stop_search_service import StopSearchEngine, haversine_distance_km

DB_URL = "sqlite:///crowdwise/backend/crowdwise.db"


@pytest.fixture(scope="module")
def search_engine():
    """Initializes StopSearchEngine loaded from the active database."""
    engine_db = create_engine(DB_URL)
    with Session(engine_db) as session:
        stops = load_all_stops(session)
    assert len(stops) > 0, "Database dim_stops table is empty"
    return StopSearchEngine(stops)


# ===========================================================================
# 1. Spatial cKDTree Search Latency SLA Benchmark (20,000 Synthetic GPS Points)
# ===========================================================================

class TestSpatialSearchCKDTreeLatencySLA:
    """Stress tests cKDTree spatial search across 20,000 synthetic GPS queries."""

    def test_20000_gps_queries_latency_sla(self, search_engine):
        """Measures p50, p95, p99, and mean latency across 20,000 synthetic GPS points."""
        np.random.seed(42)
        n_queries = 20000

        # Uniform coordinates strictly inside Delhi NCT bounds
        delhi_lats = np.random.uniform(28.40, 28.88, n_queries)
        delhi_lons = np.random.uniform(76.84, 77.38, n_queries)

        # Warmup phase (500 queries)
        for i in range(500):
            search_engine.search_nearest(delhi_lats[i], delhi_lons[i], radius_km=2.0, limit=10)

        # Measurement phase
        latencies_us = np.empty(n_queries, dtype=np.float64)

        for i in range(n_queries):
            t_start = time.perf_counter_ns()
            res = search_engine.search_nearest(delhi_lats[i], delhi_lons[i], radius_km=2.0, limit=10)
            t_end = time.perf_counter_ns()
            latencies_us[i] = (t_end - t_start) / 1000.0

        latencies_ms = latencies_us / 1000.0
        mean_ms = float(np.mean(latencies_ms))
        p50_ms = float(np.percentile(latencies_ms, 50))
        p90_ms = float(np.percentile(latencies_ms, 90))
        p95_ms = float(np.percentile(latencies_ms, 95))
        p99_ms = float(np.percentile(latencies_ms, 99))
        max_ms = float(np.max(latencies_ms))

        print(f"\n--- 20,000 GPS Search Nearest Latency Benchmark ---")
        print(f"Total time   : {np.sum(latencies_ms):.2f} ms")
        print(f"Mean latency : {mean_ms:.5f} ms")
        print(f"p50 (Median) : {p50_ms:.5f} ms")
        print(f"p90 latency  : {p90_ms:.5f} ms")
        print(f"p95 latency  : {p95_ms:.5f} ms")
        print(f"p99 latency  : {p99_ms:.5f} ms")
        print(f"Max latency  : {max_ms:.5f} ms")

        # SLA assertions: SLA requirement is < 0.20 ms
        assert mean_ms < 0.20, f"Mean latency {mean_ms:.4f}ms exceeded 0.20ms SLA"
        assert p50_ms < 0.20, f"p50 latency {p50_ms:.4f}ms exceeded 0.20ms SLA"
        assert p95_ms < 0.20, f"p95 latency {p95_ms:.4f}ms exceeded 0.20ms SLA"
        assert p99_ms < 0.20, f"p99 latency {p99_ms:.4f}ms exceeded 0.20ms SLA"

    def test_spatial_results_distance_monotonicity(self, search_engine):
        """Verifies spatial nearest results are strictly sorted by distance ascending."""
        res = search_engine.search_nearest(lat=28.6139, lon=77.2090, radius_km=5.0, limit=10)
        assert len(res) > 1
        for i in range(len(res) - 1):
            assert res[i]["distance_km"] <= res[i + 1]["distance_km"]
            assert res[i]["distance_km"] <= 5.0


# ===========================================================================
# 2. Boundary and Out-of-Bounds Coordinate Handling
# ===========================================================================

class TestSpatialSearchEdgeCasesAndBounds:
    """Verifies robustness at boundary conditions and out-of-bounds inputs."""

    @pytest.mark.parametrize(
        "city_name,lat,lon",
        [
            ("Mumbai", 19.0760, 72.8777),
            ("Bengaluru", 12.9716, 77.5946),
            ("Kolkata", 22.5726, 88.3639),
            ("Chennai", 13.0827, 80.2707),
            ("London", 51.5074, -0.1278),
            ("New York", 40.7128, -74.0060),
            ("Null Island", 0.0, 0.0),
            ("North Pole", 90.0, 0.0),
            ("South Pole", -90.0, 0.0),
            ("Just South of NCR", 26.9999, 77.2090),
            ("Just North of NCR", 30.5001, 77.2090),
            ("Just West of NCR", 28.6139, 75.4999),
            ("Just East of NCR", 28.6139, 78.5001),
        ],
    )
    def test_out_of_bounds_returns_empty_safely(self, search_engine, city_name, lat, lon):
        """Verifies coordinates outside NCR expanded boundary return empty list without crashing."""
        res = search_engine.search_nearest(lat=lat, lon=lon, radius_km=2.0)
        assert res == [], f"Expected [] for {city_name} at ({lat}, {lon}), got {res}"

    def test_non_finite_floating_coordinates(self, search_engine):
        """Verifies NaN and Inf coordinates do not throw unhandled exceptions."""
        assert search_engine.search_nearest(float("nan"), float("nan")) == []
        assert search_engine.search_nearest(float("inf"), float("inf")) == []
        assert search_engine.search_nearest(float("-inf"), float("-inf")) == []

    def test_extreme_radius_parameters(self, search_engine):
        """Verifies extreme or negative radius parameters are safely clamped [0.05..25.0]."""
        # Negative radius clamped to 0.05km
        res_neg = search_engine.search_nearest(lat=28.6139, lon=77.2090, radius_km=-5.0)
        assert isinstance(res_neg, list)

        # Zero radius clamped to 0.05km
        res_zero = search_engine.search_nearest(lat=28.6139, lon=77.2090, radius_km=0.0)
        assert isinstance(res_zero, list)

        # Huge radius clamped to 25.0km
        res_huge = search_engine.search_nearest(lat=28.6139, lon=77.2090, radius_km=10000.0)
        assert isinstance(res_huge, list)
        for r in res_huge:
            assert r["distance_km"] <= 25.0

    def test_empty_stop_search_engine(self):
        """Verifies StopSearchEngine with 0 stops gracefully returns empty results."""
        empty_engine = StopSearchEngine([])
        assert empty_engine.search_nearest(28.6139, 77.2090) == []
        assert empty_engine.search_text("Kashmere Gate") == []
        assert empty_engine.search(q="AIIMS") == []
        assert empty_engine.search(lat=28.6139, lon=77.2090) == []


# ===========================================================================
# 3. Vernacular Transliteration Recall
# ===========================================================================

class TestVernacularTransliterations:
    """Verifies colloquial Delhi spelling variations match cleanly."""

    @pytest.mark.parametrize(
        "query,expected_substring",
        [
            ("Kashmere Gate", "Kashmere Gate"),
            ("kashmiri gate", "Kashmere Gate"),
            ("isbt kashmiri gate", "ISBT Kashmere Gate"),
            ("kashmere gate isbt", "ISBT Kashmere Gate"),
            ("Dhaula Kuan", "Dhaula Kuan"),
            ("dholakuan", "Dhaula Kuan"),
            ("dhawla kuan", "Dhaula Kuan"),
            ("dhaula kuan complex", "Dhaula Kuan Complex"),
            ("AIIMS", "AIIMS"),
            ("aiims", "AIIMS"),
            ("aims", "AIIMS"),
            ("Connaught Place", "Connaught Place"),
            ("connaught", "Connaught Place"),
            ("cannaught place", "Connaught Place"),
            ("Chandni Chowk", "Chandni Chowk"),
            ("chandani chowk", "Chandni Chowk"),
            ("Anand Vihar", "Anand Vihar"),
            ("anandvihar", "Anand Vihar"),
            ("anand vihar isbt", "Anand Vihar ISBT"),
            ("Saket", "Saket"),
            ("Hauz Khas", "Hauz Khas"),
        ],
    )
    def test_transliteration_query_matches(self, search_engine, query, expected_substring):
        """Verifies each transliteration variation returns the expected bus stop."""
        results = search_engine.search_text(query, limit=5)
        assert len(results) > 0, f"Query '{query}' returned zero results"
        matched_names = [r["stop_name"] for r in results]
        assert any(
            expected_substring.lower() in name.lower() for name in matched_names
        ), f"Query '{query}' did not match '{expected_substring}'. Top matches: {matched_names}"
        assert results[0]["match_score"] >= 0.45


# ===========================================================================
# 4. Adversarial Query Inputs (SQLi, XSS, Control Chars, Whitespace)
# ===========================================================================

class TestAdversarialQueryInputs:
    """Verifies resilience against hostile, malformed, and injection payloads."""

    @pytest.mark.parametrize(
        "sqli_payload",
        [
            "' OR 1=1 --",
            "admin' --",
            "' UNION SELECT * FROM dim_stops --",
            "'; DROP TABLE dim_stops; --",
            "'; DROP TABLE dim_routes; --",
            "' OR ''='",
            "1' ORDER BY 1--",
            "1' AND 1=2 UNION SELECT 1,2,3,4,5,6--",
            "' OR (SELECT COUNT(*) FROM dim_stops) > 0 --",
            "1; SLEEP(5);",
        ],
    )
    def test_sql_injection_payloads(self, search_engine, sqli_payload):
        """Verifies SQL injection strings execute safely without database execution or crashes."""
        res = search_engine.search_text(sqli_payload)
        assert isinstance(res, list)

    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg/onload=alert('pwn')>",
            "<iframe src='evil.com'></iframe>",
        ],
    )
    def test_xss_and_html_injection_payloads(self, search_engine, xss_payload):
        """Verifies script tags and HTML injection strings execute safely."""
        res = search_engine.search_text(xss_payload)
        assert isinstance(res, list)

    def test_special_characters_and_regex_metachars(self, search_engine):
        """Verifies special punctuation, null bytes, and regex metacharacters."""
        payloads = [
            "!@#$%^&*()_+-=[]{}|;':,./<>?",
            "^.*$",
            "[a-z]+",
            "(ISBT|Metro)",
            "\\d+",
            "Kashmere\x00Gate",
            "\\x00\\x01\\x02",
        ]
        for p in payloads:
            res = search_engine.search_text(p)
            assert isinstance(res, list)

    def test_whitespace_and_empty_queries(self, search_engine):
        """Verifies empty strings and whitespace variations return empty list."""
        assert search_engine.search_text("") == []
        assert search_engine.search_text("   ") == []
        assert search_engine.search_text("\t\r\n  \n") == []
        assert search_engine.search(q="") == []
        assert search_engine.search(q="   ") == []

    def test_padded_and_internal_whitespace(self, search_engine):
        """Verifies leading/trailing and internal whitespace don't prevent match."""
        # Padded search
        res_padded = search_engine.search_text("   Kashmere Gate   ")
        assert len(res_padded) >= 1
        assert any("Kashmere Gate" in r["stop_name"] for r in res_padded)

        # Internal multiple spaces
        res_internal = search_engine.search_text("Dhaula       Kuan")
        assert len(res_internal) >= 1
        assert any("Dhaula Kuan" in r["stop_name"] for r in res_internal)

    def test_very_long_queries_dos_resilience(self, search_engine):
        """Verifies extremely long query strings do not trigger ReDoS or OOM."""
        t0 = time.perf_counter()
        res_1k = search_engine.search_text("A" * 1000)
        assert res_1k == []

        res_10k = search_engine.search_text("Z" * 10000)
        assert res_10k == []

        res_repeat = search_engine.search_text("gate " * 200)
        assert isinstance(res_repeat, list)
        elapsed = time.perf_counter() - t0
        assert elapsed < 1.0, f"Long string processing took {elapsed:.2f}s, expected < 1.0s"


# ===========================================================================
# 5. Post-Attack Database Integrity Verification
# ===========================================================================

class TestDataIntegrityPostAdversarial:
    """Verifies database tables remain completely intact after adversarial attacks."""

    def test_database_table_counts_unmodified(self):
        """Verifies row counts in all 6 compact derived tables were not altered."""
        engine_db = create_engine(DB_URL)
        with Session(engine_db) as session:
            stops_count = session.execute(select(func.count()).select_from(DimStop)).scalar()
            routes_count = session.execute(select(func.count()).select_from(DimRoute)).scalar()
            patterns_count = session.execute(select(func.count()).select_from(DimRoutePattern)).scalar()
            pattern_stops_count = session.execute(select(func.count()).select_from(RelPatternStop)).scalar()
            trip_starts_count = session.execute(select(func.count()).select_from(DimTripStart)).scalar()
            supply_count = session.execute(select(func.count()).select_from(FactRouteSupply)).scalar()

        assert stops_count == 123, f"dim_stops modified: got {stops_count}, expected 123"
        assert routes_count == 10, f"dim_routes modified: got {routes_count}, expected 10"
        assert patterns_count == 20, f"dim_route_patterns modified: got {patterns_count}, expected 20"
        assert pattern_stops_count == 290, f"rel_pattern_stops modified: got {pattern_stops_count}, expected 290"
        assert trip_starts_count == 480, f"dim_trip_starts modified: got {trip_starts_count}, expected 480"
        assert supply_count == 400, f"fact_route_supply modified: got {supply_count}, expected 400"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
