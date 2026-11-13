"""crowdwise/backend/tests/test_zones_and_search.py
Unit tests for Contiguous 8-Zone Partitioning (F04) and Multi-Modal Stop Search (F05).
Verifies mathematical partition invariants, transliteration fuzzy resilience, and cKDTree latency SLA.
"""
import time
import pytest
from app.services.stop_search_service import (
    ZonePartitioner,
    StopSearchEngine,
    haversine_distance_km,
)


class TestZonePartitioningInvariants:
    """F04: Closed-form 8-Zone Sequence Partitioning tests."""

    def test_contiguity_invariant(self):
        """Verifies that all stops assigned to any zone appear consecutively along the route."""
        for num_stops in [9, 15, 28, 41, 65, 80]:
            zones = [ZonePartitioner.assign_stop_zone(s, num_stops) for s in range(num_stops)]
            for z in set(zones):
                indices = [i for i, val in enumerate(zones) if val == z]
                # Indices must be contiguous: indices[-1] - indices[0] + 1 == len(indices)
                assert indices[-1] - indices[0] + 1 == len(indices), f"Zone {z} not contiguous for N={num_stops}"

    def test_monotonicity_invariant(self):
        """Verifies zone index never decreases as stop sequence advances: z(s) <= z(s+1)."""
        for num_stops in [5, 12, 33, 47, 75]:
            zones = [ZonePartitioner.assign_stop_zone(s, num_stops) for s in range(num_stops)]
            for i in range(len(zones) - 1):
                assert zones[i] <= zones[i + 1], f"Monotonicity violated at sequence {i} for N={num_stops}"

    def test_zone_bounds_and_completeness(self):
        """Verifies every stop sequence maps to a valid zone in [0, 7]."""
        for num_stops in [1, 4, 8, 16, 50]:
            zones = [ZonePartitioner.assign_stop_zone(s, num_stops) for s in range(num_stops)]
            assert len(zones) == num_stops
            assert min(zones) == 0
            assert max(zones) <= 7

    def test_short_feeder_route_identity_partition(self):
        """Verifies short routes with N <= 8 assign zone_id = stop_sequence without gaps."""
        assert [ZonePartitioner.assign_stop_zone(s, 4) for s in range(4)] == [0, 1, 2, 3]
        assert [ZonePartitioner.assign_stop_zone(s, 8) for s in range(8)] == [0, 1, 2, 3, 4, 5, 6, 7]

    def test_terminal_stop_guaranteed_zone_7_for_large_n(self):
        """Verifies the final stop of any route pattern with N >= 8 is always in Zone 7."""
        for n in [8, 9, 20, 35, 60, 100]:
            assert ZonePartitioner.assign_stop_zone(n - 1, n) == 7

    def test_balanced_cardinality_variance_bound(self):
        """Verifies zone stop count variance satisfies max |S_z| - min |S_z| <= 1 for N >= 8."""
        for n in [17, 25, 41, 58, 73]:
            zones = [ZonePartitioner.assign_stop_zone(s, n) for s in range(n)]
            counts = [zones.count(z) for z in range(8)]
            assert max(counts) - min(counts) <= 1, f"Variance > 1 for N={n}: counts={counts}"

    def test_invalid_and_out_of_bounds_inputs(self):
        """Verifies guard clauses on invalid inputs."""
        with pytest.raises(ValueError):
            ZonePartitioner.assign_stop_zone(0, 0)
        with pytest.raises(ValueError):
            ZonePartitioner.assign_stop_zone(0, -5)
        with pytest.raises(IndexError):
            ZonePartitioner.assign_stop_zone(-1, 10)
        with pytest.raises(IndexError):
            ZonePartitioner.assign_stop_zone(10, 10)

    def test_compute_zone_corridor_summary(self):
        """Verifies summary computation for route zones."""
        pattern_stops = [
            {"stop_id": "S1", "stop_name": "Origin", "stop_sequence": 0, "zone_id": 0, "stop_lat": 28.50, "stop_lon": 77.10, "cum_dist_km": 0.0},
            {"stop_id": "S2", "stop_name": "Mid1", "stop_sequence": 1, "zone_id": 0, "stop_lat": 28.52, "stop_lon": 77.12, "cum_dist_km": 2.5},
            {"stop_id": "S3", "stop_name": "Mid2", "stop_sequence": 2, "zone_id": 1, "stop_lat": 28.55, "stop_lon": 77.15, "cum_dist_km": 6.0},
            {"stop_id": "S4", "stop_name": "Term", "stop_sequence": 3, "zone_id": 1, "stop_lat": 28.58, "stop_lon": 77.18, "cum_dist_km": 10.0},
        ]
        summary = ZonePartitioner.compute_zone_corridor_summary(pattern_stops)
        assert len(summary) == 2
        assert summary[0]["zone_id"] == 0
        assert summary[0]["stop_count"] == 2
        assert summary[0]["start_stop_id"] == "S1"
        assert summary[0]["end_stop_id"] == "S2"
        assert summary[0]["zone_dist_km"] == 2.5
        assert summary[1]["zone_id"] == 1
        assert summary[1]["end_dist_km"] == 10.0


class TestMultiModalStopSearch:
    """F05: Exact, Prefix, Trigram Fuzzy, and Spatial cKDTree Search."""

    @pytest.fixture
    def test_stops(self):
        """Standard set of test stops in Delhi."""
        return [
            {"stop_id": "1", "stop_code": "9CE15308", "stop_name": "ISBT Kashmere Gate", "stop_lat": 28.6675, "stop_lon": 77.2285, "is_terminal": True},
            {"stop_id": "2", "stop_code": "9CE15309", "stop_name": "Kashmere Gate Metro Station", "stop_lat": 28.6668, "stop_lon": 77.2291, "is_terminal": False},
            {"stop_id": "3", "stop_code": "8BE12101", "stop_name": "Dhaula Kuan", "stop_lat": 28.5920, "stop_lon": 77.1620, "is_terminal": True},
            {"stop_id": "4", "stop_code": "8BE12102", "stop_name": "AIIMS", "stop_lat": 28.5670, "stop_lon": 77.2100, "is_terminal": False},
            {"stop_id": "5", "stop_code": "7AE10001", "stop_name": "Connaught Place (Super Bazar)", "stop_lat": 28.6328, "stop_lon": 77.2195, "is_terminal": False},
            {"stop_id": "6", "stop_code": "6BE10001", "stop_name": "Anand Vihar ISBT", "stop_lat": 28.6465, "stop_lon": 77.3150, "is_terminal": True},
        ]

    def test_exact_code_search(self, test_stops):
        """Verifies exact stop_code search returns match with score 1.00."""
        engine = StopSearchEngine(test_stops)
        res = engine.search_text("9CE15308")
        assert len(res) >= 1
        assert res[0]["stop_id"] == "1"
        assert res[0]["match_type"] == "exact_code"
        assert res[0]["match_score"] == 1.00

    def test_exact_name_search(self, test_stops):
        """Verifies exact stop_name search returns match with score 0.95."""
        engine = StopSearchEngine(test_stops)
        res = engine.search_text("Dhaula Kuan")
        assert len(res) >= 1
        assert res[0]["stop_id"] == "3"
        assert res[0]["match_type"] == "exact_name"
        assert res[0]["match_score"] == 0.95

    def test_prefix_search(self, test_stops):
        """Verifies prefix match on stop_name."""
        engine = StopSearchEngine(test_stops)
        res = engine.search_text("Connaught")
        assert len(res) >= 1
        assert res[0]["stop_id"] == "5"
        assert res[0]["match_type"] in ("prefix_name", "exact_name")

    def test_fuzzy_transliteration_resilience(self, test_stops):
        """Verifies colloquial Delhi spelling variations match cleanly with score >= 0.45."""
        engine = StopSearchEngine(test_stops)

        # "Kashmiri Gate" query against "ISBT Kashmere Gate"
        res_kg = engine.search_text("Kashmiri Gate")
        assert len(res_kg) >= 1
        assert res_kg[0]["stop_name"] in ("ISBT Kashmere Gate", "Kashmere Gate Metro Station")
        assert res_kg[0]["match_score"] >= 0.45

        # "Dholakuan" query against "Dhaula Kuan"
        res_dk = engine.search_text("Dholakuan")
        assert len(res_dk) >= 1
        assert res_dk[0]["stop_name"] == "Dhaula Kuan"
        assert res_dk[0]["match_score"] >= 0.45

    def test_spatial_nearest_search(self, test_stops):
        """Verifies cKDTree spatial nearest search returns closest stops in ascending distance order."""
        engine = StopSearchEngine(test_stops)
        # Search near Connaught Place (28.6328, 77.2195)
        res = engine.search_nearest(lat=28.6330, lon=77.2200, radius_km=2.0)
        assert len(res) >= 1
        assert res[0]["stop_id"] == "5"
        assert res[0]["distance_km"] < 0.2
        assert res[0]["match_type"] == "spatial"

    def test_spatial_nearest_latency_sla(self, test_stops):
        """Verifies 100 spatial radius queries run within SLA (<0.2ms mean latency per query)."""
        engine = StopSearchEngine(test_stops)
        lat_queries = [28.50 + (i * 0.002) for i in range(100)]
        lon_queries = [77.15 + (i * 0.002) for i in range(100)]

        # Warm up
        engine.search_nearest(28.63, 77.21, radius_km=3.0)

        t0 = time.perf_counter()
        for lat, lon in zip(lat_queries, lon_queries):
            engine.search_nearest(lat, lon, radius_km=3.0)
        total_time_ms = (time.perf_counter() - t0) * 1000.0
        avg_latency_ms = total_time_ms / 100.0

        # Mean latency must be < 0.2ms
        assert avg_latency_ms < 0.2, f"Average spatial query latency {avg_latency_ms:.4f}ms exceeded 0.2ms SLA"

    def test_out_of_bounds_spatial_query(self, test_stops):
        """Verifies coordinates far outside Delhi NCR return empty list safely."""
        engine = StopSearchEngine(test_stops)
        # Mumbai coordinates
        res = engine.search_nearest(lat=19.0760, lon=72.8777, radius_km=5.0)
        assert res == []
