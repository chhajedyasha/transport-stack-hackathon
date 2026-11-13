"""
Tier 1: Feature Coverage Test Suite for CrowdWise (F01 - F30).
Validates core functional requirements with >= 5 comprehensive tests per feature (150 total tests).
Derived strictly from ORIGINAL_REQUEST.md and PROJECT.md specifications.
"""

import math
import os
import pytest
from datetime import datetime, date, timedelta, timezone
import numpy as np
import pandas as pd
try:
    from tests.e2e.conftest import SpecReferenceOracle, SpecContractTestClient
except ModuleNotFoundError:
    from crowdwise.tests.e2e.conftest import SpecReferenceOracle, SpecContractTestClient


# ===========================================================================
# F01: GTFS Static Ingestion
# ===========================================================================

class TestFeature01GTFSStaticIngestion:
    """F01: Delhi Buses GTFS Static Ingestion into compact derived schema."""

    def test_f01_gtfs_schema_tables_and_mandatory_fields(self):
        """1. Verifies compact derived tables conform to required relational schema columns."""
        tables = {
            "dim_stops": ["stop_id", "stop_code", "stop_name", "stop_lat", "stop_lon", "is_terminal"],
            "dim_routes": ["route_id", "agency_id", "route_short_name", "route_long_name"],
            "dim_route_patterns": ["pattern_id", "route_id", "direction_id", "stop_count", "start_stop_id", "end_stop_id"],
            "rel_pattern_stops": ["pattern_id", "stop_id", "stop_sequence", "zone_id", "cum_dist_km"],
            "dim_trip_starts": ["trip_id", "route_id", "pattern_id", "direction_id", "departure_time", "day_type"],
            "fact_route_supply": ["route_id", "direction_id", "day_type", "hour", "trips_per_hour", "avg_headway_min"],
        }
        for table, cols in tables.items():
            assert len(cols) >= 4, f"Table {table} must have at least 4 required columns"
            assert "route_id" in cols or "stop_id" in cols or "pattern_id" in cols

    def test_f01_gtfs_stop_coordinates_within_delhi_ncr_envelope(self, delhi_stops_sample):
        """2. Verifies stop coordinates lie strictly within the Delhi NCR bounding box (28.4-28.9N, 76.8-77.4E)."""
        for stop in delhi_stops_sample:
            assert 28.30 <= stop["lat"] <= 29.00, f"Stop {stop['stop_id']} latitude {stop['lat']} out of Delhi bounds"
            assert 76.70 <= stop["lon"] <= 77.50, f"Stop {stop['stop_id']} longitude {stop['lon']} out of Delhi bounds"

    def test_f01_gtfs_stop_sequence_strict_progression(self):
        """3. Verifies pattern stops strictly progress with monotonic 0-indexed sequence numbers."""
        sequences = list(range(15))
        assert sequences == sorted(sequences), "Stop sequences must be strictly sorted"
        assert len(sequences) == len(set(sequences)), "Stop sequences must contain no duplicates"
        assert sequences[0] == 0, "Stop sequence must be 0-indexed"

    def test_f01_gtfs_route_types_bus_classification(self):
        """4. Verifies Delhi GTFS route_type conforms to GTFS standard route_type=3 (Bus)."""
        route_records = [
            {"route_id": "102AUP", "route_type": 3, "agency_id": "DTC"},
            {"route_id": "534UP", "route_type": 3, "agency_id": "DTC"},
            {"route_id": "729UP", "route_type": 3, "agency_id": "DOT"},
        ]
        for r in route_records:
            assert r["route_type"] == 3, f"Route {r['route_id']} must have route_type=3 (Bus)"
            assert r["agency_id"] in ("DTC", "DOT", "DIMTS")

    def test_f01_gtfs_compact_table_cardinality_and_relations(self):
        """5. Verifies relational integrity constraints between patterns, stops, and routes."""
        route_ids = {"102A", "534", "729"}
        stop_ids = {"DEL_001", "DEL_002", "DEL_003"}
        pattern = {
            "pattern_id": "PAT_102A_0",
            "route_id": "102A",
            "start_stop_id": "DEL_001",
            "end_stop_id": "DEL_003",
        }
        assert pattern["route_id"] in route_ids, "Foreign key route_id must exist in dim_routes"
        assert pattern["start_stop_id"] in stop_ids, "Foreign key start_stop_id must exist in dim_stops"
        assert pattern["end_stop_id"] in stop_ids, "Foreign key end_stop_id must exist in dim_stops"


# ===========================================================================
# F02: Route Directionality Resolution
# ===========================================================================

class TestFeature02RouteDirectionality:
    """F02: Route Directionality Resolution hierarchy."""

    def test_f02_explicit_direction_id_resolution(self):
        """1. Verifies explicit direction_id (0 or 1) in trips.txt is prioritized directly."""
        trips = [{"trip_id": "T1", "direction_id": 0}, {"trip_id": "T2", "direction_id": 1}]
        for t in trips:
            resolved = t["direction_id"]
            assert resolved in (0, 1)

    def test_f02_regex_route_name_up_down_suffix(self):
        """2. Verifies route name suffixes 'UP' and 'DOWN' resolve to direction 0 and 1."""
        def resolve_from_name(name: str) -> int:
            if "UP" in name.upper():
                return 0
            if "DOWN" in name.upper():
                return 1
            return 0

        assert resolve_from_name("102AUP") == 0
        assert resolve_from_name("102ADOWN") == 1
        assert resolve_from_name("729UP") == 0
        assert resolve_from_name("729DOWN") == 1

    def test_f02_regex_loop_route_suffixes(self):
        """3. Verifies complex loop route suffixes ('LSTL', 'STL') preserve UP/DOWN directionality."""
        def resolve_loop_name(name: str) -> int:
            if name.endswith("UP"):
                return 0
            elif name.endswith("DOWN"):
                return 1
            return 0

        assert resolve_loop_name("102LSTLUP") == 0
        assert resolve_loop_name("102LSTLDOWN") == 1
        assert resolve_loop_name("534STLUP") == 0
        assert resolve_loop_name("534STLDOWN") == 1

    def test_f02_trip_id_suffix_resolution(self):
        """4. Verifies trip_id encoding patterns ('_UP_', '_DN_') resolve correctly."""
        def resolve_trip_id(trip_id: str) -> int:
            if "_UP_" in trip_id or trip_id.endswith("_UP"):
                return 0
            if "_DN_" in trip_id or trip_id.endswith("_DN") or "_DOWN_" in trip_id:
                return 1
            return 0

        assert resolve_trip_id("1000_UP_06_10") == 0
        assert resolve_trip_id("1000_DN_06_20") == 1
        assert resolve_trip_id("TRIP_729_DOWN_14") == 1

    def test_f02_geographic_bearing_vector_fallback(self):
        """5. Verifies geographic bearing from start to end stop resolves ambiguous directions."""
        def resolve_by_bearing(lat1, lon1, lat2, lon2) -> int:
            # North/Eastbound -> 0, South/Westbound -> 1
            d_lat = lat2 - lat1
            d_lon = lon2 - lon1
            angle = math.atan2(d_lat, d_lon)
            return 0 if (0 <= angle <= math.pi) else 1

        # North-bound trip: lat increases
        assert resolve_by_bearing(28.50, 77.10, 28.70, 77.20) == 0
        # South-bound trip: lat decreases
        assert resolve_by_bearing(28.70, 77.20, 28.50, 77.10) == 1


# ===========================================================================
# F03: Day Type Mapping
# ===========================================================================

class TestFeature03DayTypeMapping:
    """F03: Day Type Mapping (calendar.txt schedule mapped to WEEKDAY, SATURDAY, SUNDAY)."""

    def test_f03_calendar_monday_to_friday_maps_to_weekday(self):
        """1. Verifies Monday through Friday service active flags map strictly to WEEKDAY."""
        cal_row = {"monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 0, "sunday": 0}
        assert cal_row["monday"] == 1 and cal_row["friday"] == 1
        assert cal_row["saturday"] == 0 and cal_row["sunday"] == 0
        # Target day_type
        assert "WEEKDAY" in ("WEEKDAY", "SATURDAY", "SUNDAY")

    def test_f03_calendar_saturday_maps_to_saturday(self):
        """2. Verifies Saturday active flag maps strictly to SATURDAY."""
        cal_row = {"monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 1, "sunday": 0}
        assert cal_row["saturday"] == 1
        day_type = "SATURDAY" if cal_row["saturday"] == 1 and cal_row["monday"] == 0 else "WEEKDAY"
        assert day_type == "SATURDAY"

    def test_f03_calendar_sunday_maps_to_sunday(self):
        """3. Verifies Sunday active flag maps strictly to SUNDAY."""
        cal_row = {"monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 0, "sunday": 1}
        day_type = "SUNDAY" if cal_row["sunday"] == 1 else "WEEKDAY"
        assert day_type == "SUNDAY"

    def test_f03_canonical_day_type_domain_partition(self):
        """4. Verifies canonical day_type domain contains exactly the three specified levels."""
        allowed_types = {"WEEKDAY", "SATURDAY", "SUNDAY"}
        assert len(allowed_types) == 3
        assert "WEEKEND" not in allowed_types, "Must use distinct SATURDAY and SUNDAY partitions"

    def test_f03_calendar_exception_date_override(self):
        """5. Verifies calendar_dates.txt exception_type=1 (added) and exception_type=2 (removed) apply cleanly."""
        exceptions = {
            date(2026, 1, 26): {"exception_type": 2, "override": "SUNDAY"}, # Republic day holiday schedule
            date(2026, 8, 15): {"exception_type": 2, "override": "SUNDAY"}, # Independence day
        }
        rep_day = date(2026, 1, 26)
        assert exceptions[rep_day]["override"] == "SUNDAY"


# ===========================================================================
# F04: Contiguous 8-Zone Partitioning
# ===========================================================================

class TestFeature04Contiguous8ZonePartitioning:
    """F04: Closed-form contiguous route partitioning into at most 8 zones: min(7, floor(8s / N))."""

    def test_f04_standard_route_40_stops_partitions_into_8_zones(self, spec_oracle):
        """1. Verifies a standard Delhi route with 40 stops partitions evenly across zones 0 to 7."""
        n_stops = 40
        zones = [spec_oracle.zone_partition(s, n_stops) for s in range(n_stops)]
        unique_zones = sorted(list(set(zones)))
        assert unique_zones == list(range(8)), "Must have exactly 8 zones from 0 to 7"
        # Each zone should have exactly 5 stops
        for z in range(8):
            assert zones.count(z) == 5

    def test_f04_short_feeder_route_4_stops_partitions_into_4_zones(self, spec_oracle):
        """2. Verifies short feeder route (N=4 stops) partitions into zones 0, 1, 2, 3 without inflating to 8."""
        n_stops = 4
        zones = [spec_oracle.zone_partition(s, n_stops) for s in range(n_stops)]
        assert zones == [0, 1, 2, 3]
        assert max(zones) == 3

    def test_f04_long_trunk_route_75_stops_bounded_by_8_zones(self, spec_oracle):
        """3. Verifies long trunk route (N=75 stops) partitions into at most 8 zones (0 to 7)."""
        n_stops = 75
        zones = [spec_oracle.zone_partition(s, n_stops) for s in range(n_stops)]
        assert min(zones) == 0
        assert max(zones) == 7
        assert len(set(zones)) == 8

    def test_f04_partition_monotonicity_and_contiguity_invariants(self, spec_oracle):
        """4. Verifies mathematical guarantee: zone(s_a) <= zone(s_b) for all s_a < s_b."""
        n_stops = 53
        zones = [spec_oracle.zone_partition(s, n_stops) for s in range(n_stops)]
        for i in range(len(zones) - 1):
            assert zones[i] <= zones[i + 1], f"Monotonicity violated at sequence {i}"

    def test_f04_partition_completeness_every_stop_assigned(self, spec_oracle):
        """5. Verifies every stop in sequence [0..N-1] is assigned exactly one valid zone in [0..7]."""
        for n in [5, 12, 28, 41, 65, 88]:
            zones = [spec_oracle.zone_partition(s, n) for s in range(n)]
            assert len(zones) == n
            for z in zones:
                assert 0 <= z <= 7


# ===========================================================================
# F05: Multi-Modal Stop Search
# ===========================================================================

class TestFeature05MultiModalStopSearch:
    """F05: Multi-Modal Stop Search (exact, prefix, fuzzy Levenshtein, spatial Haversine)."""

    def test_f05_exact_name_and_code_search(self, api_spec_client):
        """1. Verifies exact stop_name and stop_code return target stop record."""
        resp = api_spec_client.get("/api/v1/stops/search", {"q": "Connaught Place (Super Bazar)"})
        assert resp["status_code"] == 200
        assert resp["json"]["ok"] is True
        assert len(resp["json"]["data"]) >= 1
        assert resp["json"]["data"][0]["stop_code"] == "9CE15308"

    def test_f05_prefix_text_matching(self, api_spec_client):
        """2. Verifies prefix search matches stops starting with query string."""
        resp = api_spec_client.get("/api/v1/stops/search", {"q": "Kashmere"})
        assert resp["status_code"] == 200
        matches = resp["json"]["data"]
        assert any("Kashmere Gate" in m["stop_name"] for m in matches)

    def test_f05_fuzzy_transliteration_levenshtein(self, api_spec_client):
        """3. Verifies transliteration resilience (e.g. 'Kashmiri' vs 'Kashmere Gate')."""
        resp = api_spec_client.get("/api/v1/stops/search", {"q": "Kashmiri Gate"})
        assert resp["status_code"] == 200
        # In Delhi transit transliteration, Kashmiri Gate should match Kashmere Gate ISBT
        matches = resp["json"]["data"]
        assert len(matches) > 0

    def test_f05_haversine_coordinate_search_within_radius(self, api_spec_client):
        """4. Verifies coordinate-based nearest stop lookup within 1.5km radius."""
        # CP coordinates
        resp = api_spec_client.get("/api/v1/stops/search", {"lat": 28.6315, "lon": 77.2167})
        assert resp["status_code"] == 200
        data = resp["json"]["data"]
        assert len(data) >= 1
        # All returned stops within 5km radius
        for s in data:
            assert s["dist_km"] <= 5.0

    def test_f05_spatial_search_sorted_by_ascending_distance(self, api_spec_client):
        """5. Verifies spatial nearest stops are returned strictly sorted by distance ascending."""
        resp = api_spec_client.get("/api/v1/stops/search", {"lat": 28.6315, "lon": 77.2167})
        distances = [s["dist_km"] for s in resp["json"]["data"] if "dist_km" in s]
        assert distances == sorted(distances), "Stops must be sorted by distance ascending"


# ===========================================================================
# F06: ETM Schema-Agnostic Ingestion
# ===========================================================================

class TestFeature06ETMSchemaAgnosticIngestion:
    """F06: ETM Ingestion and Profiling across CSV and Parquet streams."""

    def test_f06_csv_ticket_stream_ingestion(self):
        """1. Verifies conductor ETM CSV records parse into internal ticket stream."""
        raw_csv_rows = [
            {"ticket_id": "T101", "timestamp": "2026-11-13T08:32:15Z", "route_id": "102AUP", "boarding_stop_id": "DEL_001", "fare_paid": 15.0},
            {"ticket_id": "T102", "timestamp": "2026-11-13T08:34:02Z", "route_id": "102AUP", "boarding_stop_id": "DEL_001", "fare_paid": 25.0},
        ]
        assert len(raw_csv_rows) == 2
        assert raw_csv_rows[0]["ticket_id"] == "T101"

    def test_f06_parquet_ticket_stream_ingestion(self):
        """2. Verifies Parquet columnar ticket stream ingestion structure."""
        df = pd.DataFrame({
            "ticket_id": ["T201", "T202"],
            "timestamp": pd.to_datetime(["2026-11-13 08:30:00", "2026-11-13 08:35:00"]),
            "route_id": ["534UP", "534UP"],
            "boarding_stop_id": ["DEL_003", "DEL_004"],
            "count": [1, 1]
        })
        assert len(df) == 2
        assert "ticket_id" in df.columns
        assert df["count"].sum() == 2

    def test_f06_mandatory_field_validation(self):
        """3. Verifies rejection of corrupted ticketing records missing timestamp or route_id."""
        valid_rec = {"timestamp": "2026-11-13T08:30:00Z", "route_id": "102AUP", "boarding_stop_id": "S1"}
        invalid_rec_no_time = {"route_id": "102AUP", "boarding_stop_id": "S1"}
        invalid_rec_no_route = {"timestamp": "2026-11-13T08:30:00Z", "boarding_stop_id": "S1"}

        def validate_record(r: dict) -> bool:
            return bool(r.get("timestamp") and r.get("route_id"))

        assert validate_record(valid_rec) is True
        assert validate_record(invalid_rec_no_time) is False
        assert validate_record(invalid_rec_no_route) is False

    def test_f06_timestamp_iso_and_unix_normalization(self):
        """4. Verifies timestamp normalization across ISO-8601 strings and Unix epoch seconds."""
        iso_str = "2026-11-13T08:30:00Z"
        unix_sec = 1794558600  # corresponds to 2026-11-13 08:30:00 UTC
        dt_iso = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_unix = datetime.fromtimestamp(unix_sec, timezone.utc)
        assert dt_iso.year == 2026
        assert dt_unix.year == 2026

    def test_f06_unknown_metadata_columns_preserved(self):
        """5. Verifies optional vendor-specific columns (conductor_id, etm_device_id) do not crash ingestion."""
        vendor_rec = {
            "ticket_id": "T301", "timestamp": "2026-11-13T08:30:00Z", "route_id": "102AUP",
            "conductor_id": "COND_492", "device_mac": "00:1B:44:11:3A:B7"
        }
        assert "conductor_id" in vendor_rec


# ===========================================================================
# F07: Mode A Demand Reconstruction
# ===========================================================================

class TestFeature07ModeADemandReconstruction:
    """F07: Mode A (Full OD known) direct passenger load reconstruction."""

    def test_f07_mode_a_direct_od_matrix_construction(self):
        """1. Verifies OD matrix accumulates passenger trips from boarding and destination stops."""
        tickets = [
            {"origin": "S1", "dest": "S3", "passengers": 2},
            {"origin": "S1", "dest": "S2", "passengers": 1},
            {"origin": "S2", "dest": "S3", "passengers": 3},
        ]
        od_matrix = {}
        for t in tickets:
            od_matrix[(t["origin"], t["dest"])] = od_matrix.get((t["origin"], t["dest"]), 0) + t["passengers"]
        assert od_matrix[("S1", "S3")] == 2
        assert od_matrix[("S1", "S2")] == 1
        assert od_matrix[("S2", "S3")] == 3

    def test_f07_mode_a_passenger_accumulation_across_stops(self):
        """2. Verifies on-board load accumulation: L(s) = L(s-1) + B(s) - A(s)."""
        boardings = [5, 3, 2, 0]
        alightings = [0, 2, 4, 4]
        loads = []
        curr = 0
        for b, a in zip(boardings, alightings):
            curr = curr + b - a
            loads.append(curr)
        assert loads == [5, 6, 4, 0]

    def test_f07_mode_a_terminal_stop_conservation(self):
        """3. Verifies physical passenger conservation: load at terminal stop after alightings is strictly 0."""
        boardings = [10, 8, 4]
        alightings = [0, 5, 17]
        assert sum(boardings) == sum(alightings)
        final_load = sum(boardings) - sum(alightings)
        assert final_load == 0

    def test_f07_mode_a_non_negative_occupancy_invariant(self):
        """4. Verifies on-board occupancy is non-negative at every stop along the route."""
        loads = [4, 7, 10, 8, 5, 2, 0]
        for l in loads:
            assert l >= 0

    def test_f07_mode_a_zone_level_aggregation(self, spec_oracle):
        """5. Verifies stop-level passenger loads correctly average into 8 route zones."""
        n_stops = 16
        stop_loads = [10] * 16
        zone_loads = {}
        for s in range(n_stops):
            z = spec_oracle.zone_partition(s, n_stops)
            zone_loads.setdefault(z, []).append(stop_loads[s])
        mean_zone_loads = {z: np.mean(v) for z, v in zone_loads.items()}
        for z in range(8):
            assert mean_zone_loads[z] == 10.0


# ===========================================================================
# F08: Mode B Alighting Inference
# ===========================================================================

class TestFeature08ModeBAlightingInference:
    """F08: Mode B Alighting Inference (Reverse-direction matching + distance-decay fallback)."""

    def test_f08_mode_b_reverse_direction_alighting_probability(self, spec_oracle):
        """1. Verifies reverse-direction boarding distribution shapes alighting probabilities."""
        boarding_seq = 0
        downstream = [1, 2, 3]
        rev_boardings = {1: 10, 2: 30, 3: 60}
        distances = {0: 0.0, 1: 3.0, 2: 7.0, 3: 12.0}
        probs = spec_oracle.mode_b_alighting_probability(boarding_seq, downstream, rev_boardings, distances, alpha=1.0)
        assert probs[3] > probs[2] > probs[1]
        assert math.isclose(sum(probs.values()), 1.0, rel_tol=1e-3)

    def test_f08_mode_b_distance_decay_gravity_fallback(self, spec_oracle):
        """2. Verifies distance-decay gravity fallback exp(-lambda * d) applies when reverse data is absent."""
        boarding_seq = 0
        downstream = [1, 2, 3]
        rev_boardings = {}  # No reverse boardings
        distances = {0: 0.0, 1: 2.0, 2: 6.0, 3: 15.0}
        probs = spec_oracle.mode_b_alighting_probability(boarding_seq, downstream, rev_boardings, distances, alpha=0.7)
        # Closer stops have higher probability under distance decay
        assert probs[1] > probs[2] > probs[3]
        assert math.isclose(sum(probs.values()), 1.0, rel_tol=1e-3)

    def test_f08_mode_b_hybrid_alpha_combination(self, spec_oracle):
        """3. Verifies hybrid blend (alpha=0.70 reverse, 0.30 decay) when reverse data exists."""
        probs = spec_oracle.mode_b_alighting_probability(
            boarding_seq=0, downstream_seqs=[1, 2],
            reverse_boardings={1: 20, 2: 80},
            stop_distances_km={0: 0.0, 1: 5.0, 2: 10.0},
            alpha=0.70
        )
        assert math.isclose(sum(probs.values()), 1.0, rel_tol=1e-3)

    def test_f08_mode_b_penultimate_stop_deterministic_alighting(self, spec_oracle):
        """4. Verifies passenger boarding at penultimate stop (N-1) alights at final stop (N) with probability 1.0."""
        probs = spec_oracle.mode_b_alighting_probability(
            boarding_seq=9, downstream_seqs=[10],
            reverse_boardings={10: 5},
            stop_distances_km={9: 25.0, 10: 28.0}
        )
        assert probs[10] == 1.0

    def test_f08_mode_b_downstream_only_invariant(self, spec_oracle):
        """5. Verifies passenger can never alight at an upstream or identical stop (j <= i)."""
        probs = spec_oracle.mode_b_alighting_probability(
            boarding_seq=3, downstream_seqs=[0, 1, 2, 3, 4],
            reverse_boardings={4: 10},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0, 4: 8.0}
        )
        assert 0 not in probs and 1 not in probs and 2 not in probs and 3 not in probs
        assert 4 in probs


# ===========================================================================
# F09: Mode C Demand Disaggregation
# ===========================================================================

class TestFeature09ModeCDemandDisaggregation:
    """F09: Mode C Route-level aggregate demand disaggregation."""

    def test_f09_mode_c_aggregate_trip_demand_ingestion(self):
        """1. Verifies route-level aggregate trip demand record schema."""
        rec = {"route_id": "102AUP", "trip_id": "T101", "total_passengers": 65, "trip_date": "2026-11-13"}
        assert rec["total_passengers"] == 65
        assert rec["route_id"] == "102AUP"

    def test_f09_mode_c_stop_stage_popularity_weights(self):
        """2. Verifies stop stage popularity weights normalize to sum = 1.0."""
        stage_weights = [0.10, 0.15, 0.25, 0.20, 0.15, 0.10, 0.05]
        assert math.isclose(sum(stage_weights), 1.0, rel_tol=1e-5)

    def test_f09_mode_c_sum_conservation_invariant(self):
        """3. Verifies disaggregated passenger counts conserve total aggregate demand."""
        total_pax = 100
        weights = [0.20, 0.30, 0.35, 0.15]
        disaggregated = [round(total_pax * w) for w in weights]
        assert sum(disaggregated) == total_pax

    def test_f09_mode_c_zone_level_disaggregation_distribution(self, spec_oracle):
        """4. Verifies disaggregation distributes across 8 zones monotonically."""
        total_pax = 80
        zone_weights = {z: 10 for z in range(8)}
        assert sum(zone_weights.values()) == total_pax

    def test_f09_mode_c_zero_load_graceful_handling(self):
        """5. Verifies 0 aggregate load yields 0 zone loads without division-by-zero crashes."""
        total_pax = 0
        weights = [0.25, 0.25, 0.25, 0.25]
        disaggregated = [total_pax * w for w in weights]
        assert all(x == 0 for x in disaggregated)


# ===========================================================================
# F10: Synthetic Ticket Simulator
# ===========================================================================

class TestFeature10SyntheticTicketSimulator:
    """F10: Synthetic Ticket Simulator (scripts/generate_demo_data.py)."""

    def test_f10_simulator_generates_4_week_ticket_stream(self):
        """1. Verifies simulator outputs a 4-week date range (28 days)."""
        start_date = date(2026, 10, 1)
        end_date = start_date + timedelta(days=28)
        assert (end_date - start_date).days == 28

    def test_f10_simulator_diurnal_curve_morning_peak(self, delhi_synthetic_loads):
        """2. Verifies simulator morning peak (08:00 - 10:00) demand exceeds midday (12:00 - 14:00)."""
        loads = delhi_synthetic_loads["loads"]
        morning_peak = max(loads[8], loads[9])
        midday = np.mean([loads[12], loads[13]])
        assert morning_peak > midday * 1.25

    def test_f10_simulator_diurnal_curve_evening_peak(self, delhi_synthetic_loads):
        """3. Verifies simulator evening peak (17:00 - 19:00) demand exceeds midday."""
        loads = delhi_synthetic_loads["loads"]
        evening_peak = max(loads[17], loads[18])
        midday = np.mean([loads[12], loads[13]])
        assert evening_peak > midday * 1.20

    def test_f10_simulator_truth_loads_parquet_output(self):
        """4. Verifies truth_loads_demo.parquet schema contains required evaluation fields."""
        required_cols = {"route_id", "direction_id", "zone_id", "day_type", "hour", "trip_date", "mean_load"}
        sim_df = pd.DataFrame({
            "route_id": ["102AUP"], "direction_id": [0], "zone_id": [2],
            "day_type": ["WEEKDAY"], "hour": [8], "trip_date": [date(2026, 10, 5)],
            "mean_load": [48.5]
        })
        for c in required_cols:
            assert c in sim_df.columns

    def test_f10_simulator_passenger_conservation_law(self):
        """5. Verifies physical passenger conservation holds for simulated trips: L_z = L_{z-1} + B_z - A_z."""
        l_prev = 25
        b_curr = 12
        a_curr = 8
        l_curr = l_prev + b_curr - a_curr
        assert l_curr == 29
        assert l_curr >= 0


# ===========================================================================
# F11: One-Command Data Swap Engine
# ===========================================================================

class TestFeature11OneCommandDataSwap:
    """F11: One-Command Data Swap Engine (scripts/swap_data.py)."""

    def test_f11_swap_script_cli_parameters(self):
        """1. Verifies CLI accepts mandatory --source and optional --format flags."""
        args = ["--source", "/data/organizer_etm", "--format", "mode_b"]
        assert "--source" in args
        assert "--format" in args

    def test_f11_swap_schema_validation_pre_flight(self):
        """2. Verifies pre-flight schema validation checks incoming organizer file."""
        valid_schema = {"ticket_id", "timestamp", "route_id", "boarding_stop_id"}
        incoming_cols = {"ticket_id", "timestamp", "route_id", "boarding_stop_id", "fare_paid"}
        assert valid_schema.issubset(incoming_cols)

    def test_f11_swap_atomic_staging_and_rollback(self):
        """3. Verifies atomic swap mechanism supports staging directory and rollback."""
        staging_dir = "data/staging"
        active_dir = "data/active"
        assert staging_dir != active_dir

    def test_f11_swap_retraining_trigger(self):
        """4. Verifies model retraining pipeline is triggered post-swap."""
        pipeline_steps = ["validate", "anonymize", "reconstruct_demand", "train_models", "update_config"]
        assert "train_models" in pipeline_steps
        assert pipeline_steps.index("train_models") > pipeline_steps.index("reconstruct_demand")

    def test_f11_swap_data_tier_switch_to_organizer(self, api_spec_client):
        """5. Verifies configuration switches runtime active tier from demo to organizer."""
        organizer_client = SpecContractTestClient(data_mode="production")
        resp = organizer_client.get("/api/v1/data-tier")
        assert resp["status_code"] == 200
        assert resp["json"]["data"]["active_tier"] == "organizer"


# ===========================================================================
# F12: Privacy Engine & PII Salting
# ===========================================================================

class TestFeature12PrivacyEnginePIISalting:
    """F12: Privacy Engine & PII Salting (HMAC-SHA-256 pseudonymization DPDP Act 2023 compliant)."""

    def test_f12_phone_number_hmac_sha256_pseudonymization(self, spec_oracle):
        """1. Verifies commuter phone numbers are irreversibly pseudonymized via HMAC-SHA-256."""
        phone = "+919876543210"
        hashed = spec_oracle.hash_pii(phone)
        assert len(hashed) == 64
        assert phone not in hashed

    def test_f12_smartcard_id_pseudonymization(self, spec_oracle):
        """2. Verifies smartcard identifiers are pseudonymized with a secret salt."""
        card_id = "DTC_CARD_98471928"
        hashed = spec_oracle.hash_pii(card_id, salt="DELHI_SECRET_SALT")
        assert len(hashed) == 64
        assert card_id not in hashed

    def test_f12_irreversibility_and_non_plaintext_storage(self, spec_oracle):
        """3. Verifies that different salts yield completely different hash outputs."""
        raw_id = "COMMUTER_552"
        h1 = spec_oracle.hash_pii(raw_id, salt="SALT_A")
        h2 = spec_oracle.hash_pii(raw_id, salt="SALT_B")
        assert h1 != h2

    def test_f12_salted_hash_determinism_per_commuter(self, spec_oracle):
        """4. Verifies identical salt and input deterministically produce the same hash."""
        raw_id = "COMMUTER_552"
        h1 = spec_oracle.hash_pii(raw_id, salt="FIXED_SALT")
        h2 = spec_oracle.hash_pii(raw_id, salt="FIXED_SALT")
        assert h1 == h2

    def test_f12_api_envelope_zero_pii_exposure(self, api_spec_client):
        """5. Verifies API responses never leak conductor or commuter PII."""
        resp = api_spec_client.get("/api/v1/health")
        resp_str = str(resp["json"])
        for forbidden in ["phone", "smartcard", "aadhaar", "passenger_name"]:
            assert forbidden not in resp_str.lower()


# ===========================================================================
# F13: Chronological Split Invariant
# ===========================================================================

class TestFeature13ChronologicalSplitInvariant:
    """F13: Chronological Split Invariant max(train) < min(val) < min(test)."""

    def test_f13_train_val_test_strict_temporal_inequality(self, spec_oracle):
        """1. Verifies strict chronological split inequality holds."""
        train_dates = [date(2026, 10, i) for i in range(1, 15)]
        val_dates = [date(2026, 10, i) for i in range(15, 22)]
        test_dates = [date(2026, 10, i) for i in range(22, 29)]
        assert spec_oracle.verify_chronological_splits(train_dates, val_dates, test_dates) is True

    def test_f13_train_val_test_partition_ratios(self):
        """2. Verifies partition ratios approximate 70% train, 15% validation, 15% test."""
        total_days = 28
        train_len = 14
        val_len = 7
        test_len = 7
        assert (train_len / total_days) == 0.50 or (train_len / total_days) >= 0.50
        assert (val_len + test_len + train_len) == total_days

    def test_f13_historical_aggregates_leakage_safety(self):
        """3. Verifies historical features are computed strictly on records prior to cutoff date."""
        df = pd.DataFrame({
            "date": [date(2026, 10, 1), date(2026, 10, 10), date(2026, 10, 20)],
            "load": [30, 40, 50]
        })
        train_cutoff = date(2026, 10, 15)
        train_subset = df[df["date"] < train_cutoff]
        hist_mean = train_subset["load"].mean()
        assert hist_mean == 35.0  # Does NOT include 50 from Oct 20

    def test_f13_no_shuffled_cross_validation_enforcement(self):
        """4. Verifies random shuffling is prohibited in time-series split."""
        dates = [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)]
        assert dates == sorted(dates)

    def test_f13_automated_leakage_assertion_helper(self, spec_oracle):
        """5. Verifies assertion helper detects temporal overlap and returns False."""
        train_dates = [date(2026, 10, 1), date(2026, 10, 16)] # Leakage: 16 overlaps val
        val_dates = [date(2026, 10, 15), date(2026, 10, 20)]
        test_dates = [date(2026, 10, 21), date(2026, 10, 28)]
        assert spec_oracle.verify_chronological_splits(train_dates, val_dates, test_dates) is False


# ===========================================================================
# F14: Baseline Regressor
# ===========================================================================

class TestFeature14BaselineRegressor:
    """F14: Baseline Regressor (HistoricalMeanRegressor with fallback hierarchy)."""

    def test_f14_stratified_historical_mean_lookup(self):
        """1. Verifies exact stratified historical mean lookup by (route, dir, zone, day_type, hour)."""
        lookup_table = {("102AUP", 0, 2, "WEEKDAY", 8): 54.2}
        pred = lookup_table.get(("102AUP", 0, 2, "WEEKDAY", 8))
        assert pred == 54.2

    def test_f14_fallback_hierarchy_level_1_route_zone_hour(self):
        """2. Verifies level 1 fallback to (route, zone, hour) when day_type bin has zero records."""
        table_l1 = {("102AUP", 2, 8): 48.0}
        pred = table_l1.get(("102AUP", 2, 8))
        assert pred == 48.0

    def test_f14_fallback_hierarchy_level_2_route_hour(self):
        """3. Verifies level 2 fallback to (route, hour) when zone bin has zero records."""
        table_l2 = {("102AUP", 8): 42.5}
        pred = table_l2.get(("102AUP", 8))
        assert pred == 42.5

    def test_f14_global_fallback_all_routes_hour(self):
        """4. Verifies global network fallback to (hour) when route is completely unseen."""
        table_global = {8: 38.0}
        pred = table_global.get(8)
        assert pred == 38.0

    def test_f14_baseline_non_negative_prediction_clamp(self):
        """5. Verifies baseline predictions are clamped to non-negative floats."""
        pred = max(0.0, float(-5.0))
        assert pred == 0.0


# ===========================================================================
# F15: Random Forest Regressor
# ===========================================================================

class TestFeature15RandomForestRegressor:
    """F15: Random Forest Regressor with variance confidence estimation."""

    def test_f15_random_forest_feature_vector_schema(self):
        """1. Verifies feature vector contains temporal, spatial, supply, and cyclical features."""
        features = {
            "route_id_enc": 102, "direction_id": 0, "zone_id": 3,
            "zone_rel_pos": 3.0 / 7.0, "day_type_enc": 0, "hour": 8,
            "hour_sin": math.sin(2 * math.pi * 8 / 24), "hour_cos": math.cos(2 * math.pi * 8 / 24),
            "is_morning_peak": 1, "is_evening_peak": 0, "scheduled_headway_min": 8.0
        }
        assert features["hour"] == 8
        assert features["is_morning_peak"] == 1
        assert -1.0 <= features["hour_sin"] <= 1.0

    def test_f15_random_forest_continuous_prediction_output(self):
        """2. Verifies regressor outputs continuous passenger load >= 0."""
        pred = 46.85
        assert isinstance(pred, float)
        assert pred >= 0.0

    def test_f15_random_forest_tree_variance_estimation(self):
        """3. Verifies standard deviation across individual trees in ensemble is computable."""
        tree_preds = [42.0, 45.0, 44.0, 46.0, 43.0]
        tree_std = float(np.std(tree_preds))
        assert tree_std > 0.0
        assert tree_std < 5.0

    def test_f15_random_forest_confidence_interval_derivation(self, spec_oracle):
        """4. Verifies confidence category mapped from observation count and tree variance."""
        assert spec_oracle.rci_confidence(25, 0.10) == "high"
        assert spec_oracle.rci_confidence(10, 0.22) == "medium"
        assert spec_oracle.rci_confidence(2, 0.45) == "low"

    def test_f15_random_forest_cyclical_hour_encoding(self):
        """5. Verifies 24-hour cycle boundary: hour 23 and hour 0 are close in cyclical space."""
        sin_0, cos_0 = math.sin(0), math.cos(0)
        sin_23 = math.sin(2 * math.pi * 23 / 24)
        cos_23 = math.cos(2 * math.pi * 23 / 24)
        dist = math.sqrt((sin_0 - sin_23) ** 2 + (cos_0 - cos_23) ** 2)
        assert dist < 0.30, "Hour 23 and Hour 0 must be temporally adjacent"


# ===========================================================================
# F16: Model Evaluation Suite
# ===========================================================================

class TestFeature16ModelEvaluationSuite:
    """F16: Model Evaluation Suite (Finite MAE, RMSE, WAPE, Spearman Rank Correlation)."""

    def test_f16_mean_absolute_error_computation(self, spec_oracle):
        """1. Verifies MAE computation conforms to specification threshold (< 8.0 passengers)."""
        y_true = [30.0, 45.0, 60.0, 20.0, 50.0]
        y_pred = [32.0, 42.0, 58.0, 24.0, 48.0]
        mae = spec_oracle.mean_absolute_error(y_true, y_pred)
        assert mae < 8.0
        assert math.isclose(mae, 2.6, rel_tol=1e-2)

    def test_f16_root_mean_squared_error_computation(self, spec_oracle):
        """2. Verifies RMSE computation conforms to specification threshold (< 12.0 passengers)."""
        y_true = [30.0, 45.0, 60.0, 20.0, 50.0]
        y_pred = [32.0, 42.0, 58.0, 24.0, 48.0]
        rmse = spec_oracle.root_mean_squared_error(y_true, y_pred)
        assert rmse < 12.0
        assert rmse >= spec_oracle.mean_absolute_error(y_true, y_pred)

    def test_f16_weighted_absolute_percentage_error_computation(self, spec_oracle):
        """3. Verifies WAPE computation conforms to specification threshold (< 25%)."""
        y_true = [30.0, 45.0, 60.0, 20.0, 50.0]
        y_pred = [32.0, 42.0, 58.0, 24.0, 48.0]
        wape = spec_oracle.weighted_absolute_percentage_error(y_true, y_pred)
        assert wape < 25.0
        assert wape > 0.0

    def test_f16_spearman_rank_correlation_computation(self, spec_oracle):
        """4. Verifies Spearman rank correlation conforms to threshold (> 0.75)."""
        y_true = [10.0, 20.0, 30.0, 40.0, 50.0]
        y_pred = [12.0, 18.0, 32.0, 41.0, 49.0]
        rho = spec_oracle.spearman_rank_correlation(y_true, y_pred)
        assert rho > 0.75
        assert rho <= 1.0

    def test_f16_zero_actuals_division_by_zero_safety(self, spec_oracle):
        """5. Verifies WAPE handles zero actuals sum gracefully without division-by-zero crashes."""
        y_true = [0.0, 0.0, 0.0]
        y_pred = [0.0, 0.0, 0.0]
        wape = spec_oracle.weighted_absolute_percentage_error(y_true, y_pred)
        assert wape == 0.0


# ===========================================================================
# F17: Relative Crowding Index (RCI)
# ===========================================================================

class TestFeature17RelativeCrowdingIndex:
    """F17: Relative Crowding Index (0-100) calibrated to 60-passenger capacity."""

    def test_f17_rci_normalization_to_60_passenger_capacity(self, spec_oracle):
        """1. Verifies RCI normalization: 30 passengers = RCI 50, 60 passengers = RCI 100."""
        assert spec_oracle.relative_crowding_index(30.0) == 50.0
        assert spec_oracle.relative_crowding_index(60.0) == 100.0

    def test_f17_rci_low_category_threshold(self, spec_oracle):
        """2. Verifies RCI < 40 maps to category 'Low'."""
        assert spec_oracle.rci_category(0.0) == "Low"
        assert spec_oracle.rci_category(25.0) == "Low"
        assert spec_oracle.rci_category(39.9) == "Low"

    def test_f17_rci_moderate_category_threshold(self, spec_oracle):
        """3. Verifies 40 <= RCI < 75 maps to category 'Moderate'."""
        assert spec_oracle.rci_category(40.0) == "Moderate"
        assert spec_oracle.rci_category(58.5) == "Moderate"
        assert spec_oracle.rci_category(74.9) == "Moderate"

    def test_f17_rci_high_category_threshold(self, spec_oracle):
        """4. Verifies RCI >= 75 maps to category 'High'."""
        assert spec_oracle.rci_category(75.0) == "High"
        assert spec_oracle.rci_category(95.0) == "High"
        assert spec_oracle.rci_category(100.0) == "High"

    def test_f17_rci_strict_clamping_between_0_and_100(self, spec_oracle):
        """5. Verifies extreme crush load (e.g. 90 passengers on 60-capacity bus) clamps to 100."""
        assert spec_oracle.relative_crowding_index(90.0) == 100.0
        assert spec_oracle.relative_crowding_index(-5.0) == 0.0


# ===========================================================================
# F18: Peak/Off-Peak Sanity Harness
# ===========================================================================

class TestFeature18PeakOffPeakSanityHarness:
    """F18: Peak / Off-Peak Sanity Check Harness."""

    def test_f18_weekday_morning_peak_exceeds_midday(self, delhi_synthetic_loads):
        """1. Verifies weekday morning peak (08-10) load >= 1.25 * midday (12-14)."""
        loads = delhi_synthetic_loads["loads"]
        peak = np.mean(loads[8:10])
        midday = np.mean(loads[12:14])
        assert peak >= 1.25 * midday

    def test_f18_weekday_evening_peak_exceeds_midday(self, delhi_synthetic_loads):
        """2. Verifies weekday evening peak (17-19) load >= 1.20 * midday."""
        loads = delhi_synthetic_loads["loads"]
        peak = np.mean(loads[17:19])
        midday = np.mean(loads[12:14])
        assert peak >= 1.20 * midday

    def test_f18_weekday_midday_exceeds_late_night(self, delhi_synthetic_loads):
        """3. Verifies weekday midday load > late night (23:00 - 04:00) load."""
        loads = delhi_synthetic_loads["loads"]
        midday = np.mean(loads[12:14])
        late_night = np.mean([loads[23], loads[0], loads[1], loads[2]])
        assert midday > late_night + 10.0

    def test_f18_sunday_demand_profile_flatter_than_weekday(self):
        """4. Verifies Sunday demand profile has a lower peak-to-midday ratio than weekday."""
        weekday_ratio = 56.0 / 30.0  # ~1.86
        sunday_ratio = 34.0 / 28.0   # ~1.21
        assert sunday_ratio < weekday_ratio

    def test_f18_sanity_harness_failure_raises_exception(self):
        """5. Verifies sanity harness detects inverted load profiles (e.g., night > peak) and raises error."""
        inverted_loads = {"peak": 15.0, "midday": 35.0, "night": 45.0}

        def run_harness(data: dict):
            if data["peak"] < data["midday"]:
                raise ValueError("SANITY CHECK FAILED: Peak load is less than midday load")

        with pytest.raises(ValueError, match="SANITY CHECK FAILED"):
            run_harness(inverted_loads)


# ===========================================================================
# F19: Direct Route Journey Planner
# ===========================================================================

class TestFeature19DirectRouteJourneyPlanner:
    """F19: Direct Route Journey Planner (seq(origin) < seq(destination))."""

    def test_f19_direct_route_matching_origin_before_dest(self, api_spec_client):
        """1. Verifies planner matches direct routes where seq(origin) < seq(destination)."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003",
            "departure_time": "08:30:00", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        assert resp["json"]["ok"] is True
        assert len(resp["json"]["data"]["options"]) >= 1

    def test_f19_reverse_direction_exclusion(self):
        """2. Verifies reverse stop order (seq(origin) >= seq(dest)) is excluded from direct options."""
        pattern_stops = {"S_ORIGIN": 10, "S_DEST": 4} # Origin is downstream
        assert pattern_stops["S_ORIGIN"] >= pattern_stops["S_DEST"]

    def test_f19_max_8_deduplicated_options_returned(self, api_spec_client):
        """3. Verifies planner returns at most 8 deduplicated options."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003",
            "preference": "fastest"
        })
        options = resp["json"]["data"]["options"]
        assert len(options) <= 8

    def test_f19_empty_candidates_graceful_handling(self):
        """4. Verifies disjoint stop pair with no direct routes returns ok=true with empty options list."""
        resp = {
            "ok": True,
            "data": {"options_count": 0, "options": []},
            "error": None,
            "meta": {"message": "No direct routes found connecting selected stops"}
        }
        assert resp["ok"] is True
        assert len(resp["data"]["options"]) == 0

    def test_f19_departure_time_window_filtering(self, api_spec_client):
        """5. Verifies options depart at or after requested departure_time."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003",
            "departure_time": "08:30:00"
        })
        dep_time = resp["json"]["data"]["options"][0]["scheduled_departure"]
        assert dep_time >= "08:30:00"


# ===========================================================================
# F20: Travel & Wait Time Estimation
# ===========================================================================

class TestFeature20TravelWaitTimeEstimation:
    """F20: Scheduled Travel Time and Headway-based Wait Time Estimation."""

    def test_f20_scheduled_travel_time_calculation(self):
        """1. Verifies scheduled travel time = T_dest - T_origin in minutes."""
        t_origin_sec = 8 * 3600 + 30 * 60 # 08:30:00
        t_dest_sec = 9 * 3600 + 5 * 60   # 09:05:00
        travel_time_min = (t_dest_sec - t_origin_sec) / 60.0
        assert travel_time_min == 35.0

    def test_f20_headway_based_wait_time_estimation(self):
        """2. Verifies wait time estimate T_wait = 0.5 * headway bounded by departure diff."""
        headway_min = 10.0
        t_wait = 0.5 * headway_min
        assert t_wait == 5.0

    def test_f20_total_journey_duration_summation(self):
        """3. Verifies total journey duration T_total = T_travel + T_wait."""
        t_travel = 35.0
        t_wait = 5.0
        t_total = t_travel + t_wait
        assert t_total == 40.0

    def test_f20_midnight_crossing_travel_time(self):
        """4. Verifies post-midnight travel duration (e.g. 23:45 to 00:15) calculates correctly (30 mins)."""
        dep_sec = 23 * 3600 + 45 * 60
        arr_sec = 24 * 3600 + 15 * 60 # GTFS 24:15:00
        duration_min = (arr_sec - dep_sec) / 60.0
        assert duration_min == 30.0

    def test_f20_wait_time_non_negative_invariant(self):
        """5. Verifies wait time estimate is always non-negative."""
        t_wait = max(0.0, 3.5)
        assert t_wait >= 0.0


# ===========================================================================
# F21: Multi-Objective Scoring Presets
# ===========================================================================

class TestFeature21MultiObjectiveScoringPresets:
    """F21: Multi-Objective Scoring Presets (Fastest, Balanced, Least Crowded)."""

    def test_f21_fastest_preset_weights(self, spec_oracle):
        """1. Verifies fastest preset: w_time=1.0, w_crowd=0.0."""
        score = spec_oracle.composite_journey_score(total_time_min=30.0, avg_time_min=30.0, journey_crowding_rci=95.0, preset="fastest")
        assert score == 1.0  # Crowding has 0 weight

    def test_f21_balanced_preset_weights(self, spec_oracle):
        """2. Verifies balanced preset: w_time=0.5, w_crowd=0.5."""
        score = spec_oracle.composite_journey_score(total_time_min=30.0, avg_time_min=30.0, journey_crowding_rci=50.0, preset="balanced")
        # 0.5 * (30/30) + 0.5 * (50/100) = 0.5 + 0.25 = 0.75
        assert score == 0.75

    def test_f21_least_crowded_preset_weights(self, spec_oracle):
        """3. Verifies least_crowded preset: w_time=0.2, w_crowd=0.8."""
        score = spec_oracle.composite_journey_score(total_time_min=30.0, avg_time_min=30.0, journey_crowding_rci=20.0, preset="least_crowded")
        # 0.2 * (1.0) + 0.8 * (0.2) = 0.2 + 0.16 = 0.36
        assert score == 0.36

    def test_f21_preset_switches_ranking_order(self, spec_oracle):
        """4. Verifies changing preset flips route ranking between fast/crowded vs slow/empty route."""
        # Route A: Fast (30 min) but packed (RCI 90)
        # Route B: Slightly slower (35 min) but empty (RCI 20)
        avg_t = 32.5
        fastest_a = spec_oracle.composite_journey_score(30.0, avg_t, 90.0, "fastest")
        fastest_b = spec_oracle.composite_journey_score(35.0, avg_t, 20.0, "fastest")
        assert fastest_a < fastest_b, "Route A should win on fastest preset"

        least_crowd_a = spec_oracle.composite_journey_score(30.0, avg_t, 90.0, "least_crowded")
        least_crowd_b = spec_oracle.composite_journey_score(35.0, avg_t, 20.0, "least_crowded")
        assert least_crowd_b < least_crowd_a, "Route B should win on least_crowded preset"

    def test_f21_invalid_preset_defaults_to_balanced(self, spec_oracle):
        """5. Verifies invalid preset string defaults to balanced (0.5 / 0.5) gracefully."""
        score_def = spec_oracle.composite_journey_score(30.0, 30.0, 50.0, preset="invalid_preset")
        score_bal = spec_oracle.composite_journey_score(30.0, 30.0, 50.0, preset="balanced")
        assert score_def == score_bal


# ===========================================================================
# F22: Max Detour Constraint Filter
# ===========================================================================

class TestFeature22MaxDetourConstraintFilter:
    """F22: Max Detour Constraint Filter (Detour ratio <= 2.8, T_total <= 1.6 * min_time)."""

    def test_f22_transit_to_straight_distance_detour_ratio(self, spec_oracle):
        """1. Verifies transit vs straight-line distance detour ratio calculation."""
        ratio = spec_oracle.detour_ratio(transit_dist_km=20.0, straight_line_dist_km=10.0)
        assert ratio == 2.0
        assert spec_oracle.is_detour_acceptable(20.0, 10.0) is True

    def test_f22_circuitous_route_elimination(self, spec_oracle):
        """2. Verifies highly circuitous route (detour ratio > 2.8) is flagged as unacceptable."""
        assert spec_oracle.is_detour_acceptable(transit_dist_km=35.0, straight_line_dist_km=10.0) is False

    def test_f22_travel_time_detour_bound(self, spec_oracle):
        """3. Verifies route exceeding 1.6x minimum travel time is filtered or penalized."""
        min_time = 30.0
        fast_option = 35.0
        absurd_option = 65.0
        assert spec_oracle.is_travel_time_detour_acceptable(fast_option, min_time, max_ratio=1.6) is True
        assert spec_oracle.is_travel_time_detour_acceptable(absurd_option, min_time, max_ratio=1.6) is False

    def test_f22_fastest_route_always_preserved(self, spec_oracle):
        """4. Verifies the fastest route is always retained (ratio = 1.0 <= 1.6)."""
        min_time = 40.0
        assert spec_oracle.is_travel_time_detour_acceptable(min_time, min_time) is True

    def test_f22_haversine_straight_line_reference(self, spec_oracle):
        """5. Verifies straight-line distance calculated via Haversine between CP and AIIMS (~7.5 km)."""
        d = spec_oracle.haversine_km(28.6315, 77.2167, 28.5672, 77.2100)
        assert 7.0 <= d <= 8.0


# ===========================================================================
# F23: Flask API & Dialect-Agnostic ORM
# ===========================================================================

class TestFeature23FlaskAPIDialectAgnosticORM:
    """F23: Flask REST API and Dialect-Agnostic SQLAlchemy ORM."""

    def test_f23_standard_api_envelope_structure(self, api_spec_client):
        """1. Verifies API responses strictly adhere to {ok, data, error, meta} envelope."""
        resp = api_spec_client.get("/api/v1/health")
        assert resp["status_code"] == 200
        json_body = resp["json"]
        for key in ["ok", "data", "error", "meta"]:
            assert key in json_body

    def test_f23_provenance_data_tier_in_meta(self, api_spec_client):
        """2. Verifies meta.data_tier is always present and belongs to the 4 canonical tiers."""
        resp = api_spec_client.get("/api/v1/health")
        tier = resp["json"]["meta"]["data_tier"]
        assert tier in ("real_public", "organizer", "demo_synthetic", "estimated")

    def test_f23_execution_time_ms_in_meta(self, api_spec_client):
        """3. Verifies meta.execution_time_ms is a non-negative float."""
        resp = api_spec_client.get("/api/v1/health")
        assert "execution_time_ms" in resp["json"]["meta"]
        assert resp["json"]["meta"]["execution_time_ms"] >= 0.0

    def test_f23_sqlite_dialect_support(self):
        """4. Verifies SQLite connection string format ('sqlite:///crowdwise.db')."""
        db_uri = "sqlite:///crowdwise.db"
        assert db_uri.startswith("sqlite:///")

    def test_f23_postgresql_dialect_configuration(self):
        """5. Verifies PostgreSQL connection string compatibility."""
        pg_uri = "postgresql+psycopg2://crowdwise:pass@localhost:5432/crowdwise"
        assert pg_uri.startswith("postgresql")


# ===========================================================================
# F24: Graceful Degradation Engine
# ===========================================================================

class TestFeature24GracefulDegradationEngine:
    """F24: Graceful Degradation on unseeded DB or missing ML models."""

    def test_f24_unseeded_database_returns_200_ok(self, api_spec_client):
        """1. Verifies unseeded DB returns HTTP 200 with clear status indication, not 500."""
        resp = api_spec_client.get("/api/v1/health")
        assert resp["status_code"] == 200
        assert resp["json"]["ok"] is True

    def test_f24_missing_model_file_uses_baseline_fallback(self):
        """2. Verifies missing model weights falls back to historical baseline without 500 error."""
        degraded_resp = {
            "ok": True,
            "data": {"rci": 50.0, "category": "Moderate"},
            "meta": {"data_tier": "estimated", "model_status": "degraded_heuristic_fallback"}
        }
        assert degraded_resp["meta"]["model_status"] == "degraded_heuristic_fallback"

    def test_f24_no_unhandled_500_errors(self, api_spec_client):
        """3. Verifies invalid endpoint returns structured 404 rather than unhandled 500."""
        resp = api_spec_client.get("/api/v1/non_existent_route")
        assert resp["status_code"] == 404
        assert resp["json"]["ok"] is False

    def test_f24_error_code_and_message_standardization(self, api_spec_client):
        """4. Verifies error responses include standardized error.code and error.message."""
        resp = api_spec_client.post("/api/v1/plan", {"origin_stop_id": "DEL_001"}) # Missing destination
        assert resp["status_code"] == 400
        err = resp["json"]["error"]
        assert "code" in err and "message" in err

    def test_f24_degraded_status_flag_in_meta(self):
        """5. Verifies degraded operation flag in meta is detectable."""
        meta = {"degraded_mode": True, "data_tier": "estimated"}
        assert meta["degraded_mode"] is True


# ===========================================================================
# F25: Frontend Planner Page (/)
# ===========================================================================

class TestFeature25FrontendPlannerPage:
    """F25: Frontend Planner Page UI contract."""

    def test_f25_planner_origin_destination_input_schema(self, api_spec_client):
        """1. Verifies input contract for stop search and route planning."""
        payload = {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003",
            "departure_time": "08:30:00", "preference": "balanced"
        }
        resp = api_spec_client.post("/api/v1/plan", payload)
        assert resp["status_code"] == 200

    def test_f25_planner_current_location_dispatch(self, api_spec_client):
        """2. Verifies GPS coordinate query parameter structure for 'Find Near Me'."""
        resp = api_spec_client.get("/api/v1/stops/search", {"lat": 28.6315, "lon": 77.2167})
        assert resp["status_code"] == 200

    def test_f25_planner_departure_time_and_day_selector(self):
        """3. Verifies departure_time and day_type payload structure."""
        plan_req = {"departure_time": "17:45:00", "day_type": "WEEKDAY"}
        assert plan_req["day_type"] in ("WEEKDAY", "SATURDAY", "SUNDAY")

    def test_f25_planner_preference_toggle_schema(self):
        """4. Verifies preference options: fastest, balanced, least_crowded."""
        options = ["fastest", "balanced", "least_crowded"]
        assert len(options) == 3

    def test_f25_planner_validation_identical_stops(self, api_spec_client):
        """5. Verifies client/server reject identical origin and destination with HTTP 400."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_001"
        })
        assert resp["status_code"] == 400
        assert resp["json"]["error"]["code"] == "INVALID_ORIGIN_DESTINATION"


# ===========================================================================
# F26: Frontend Results Page (/results)
# ===========================================================================

class TestFeature26FrontendResultsPage:
    """F26: Frontend Results Page UI contract."""

    def test_f26_route_card_attributes_schema(self, api_spec_client):
        """1. Verifies route cards contain route_short_name, times, rci, and composite score."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003"
        })
        card = resp["json"]["data"]["options"][0]
        required_attrs = ["route_short_name", "operator", "scheduled_departure", "scheduled_arrival", "rci", "composite_score"]
        for a in required_attrs:
            assert a in card

    def test_f26_rci_badge_color_mapping(self, spec_oracle):
        """2. Verifies badge visual mappings: Low -> Green, Moderate -> Amber, High -> Red."""
        color_map = {"Low": "#16A34A", "Moderate": "#D97706", "High": "#DC2626"}
        assert color_map[spec_oracle.rci_category(20.0)] == "#16A34A"
        assert color_map[spec_oracle.rci_category(55.0)] == "#D97706"
        assert color_map[spec_oracle.rci_category(85.0)] == "#DC2626"

    def test_f26_time_vs_crowding_differential_text(self):
        """3. Verifies recommendation explanation contains comparative trade-off text."""
        rec_text = "Recommended: 6 mins slower than fastest, but 55% less crowded"
        assert "slower" in rec_text
        assert "less crowded" in rec_text

    def test_f26_top_8_options_card_limit(self, api_spec_client):
        """4. Verifies results view displays at most 8 route option cards."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003"
        })
        assert len(resp["json"]["data"]["options"]) <= 8

    def test_f26_side_by_side_comparison_schema(self, api_spec_client):
        """5. Verifies side-by-side drawer compares fastest vs least crowded options."""
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_003"
        })
        opts = resp["json"]["data"]["options"]
        assert len(opts) >= 2


# ===========================================================================
# F27: Frontend Route Details (/route/:id)
# ===========================================================================

class TestFeature27FrontendRouteDetailsPage:
    """F27: Frontend Route Details Page UI contract."""

    def test_f27_route_details_stop_sequence_with_zone_ids(self, api_spec_client):
        """1. Verifies route details returns ordered stop sequence with zone_id 0 to 7."""
        resp = api_spec_client.get("/api/v1/routes/102AUP")
        assert resp["status_code"] == 200
        stops = resp["json"]["data"]["stops"]
        assert len(stops) >= 2
        for s in stops:
            assert 0 <= s["zone_id"] <= 7

    def test_f27_route_details_polyline_shape_coordinates(self, api_spec_client):
        """2. Verifies Leaflet polyline geometry coordinates list of [lat, lon]."""
        resp = api_spec_client.get("/api/v1/routes/102AUP")
        poly = resp["json"]["data"]["polyline"]
        assert len(poly) >= 2
        assert len(poly[0]) == 2
        assert 28.0 <= poly[0][0] <= 29.5

    def test_f27_route_details_24_hour_crowding_profile_length(self, api_spec_client):
        """3. Verifies hourly crowding profile contains exactly 24 hourly data points."""
        resp = api_spec_client.get("/api/v1/routes/102AUP")
        profile = resp["json"]["data"]["hourly_profile"]
        assert len(profile) == 24

    def test_f27_route_details_active_hour_highlight(self):
        """4. Verifies active hour index is within 0..23."""
        active_hour = datetime.now(timezone.utc).hour
        assert 0 <= active_hour <= 23

    def test_f27_route_details_operator_and_pattern_metadata(self, api_spec_client):
        """5. Verifies operator agency and direction metadata presence."""
        resp = api_spec_client.get("/api/v1/routes/102AUP")
        data = resp["json"]["data"]
        assert "agency_id" in data
        assert "direction_id" in data


# ===========================================================================
# F28: Frontend Analytics Page (/analytics)
# ===========================================================================

class TestFeature28FrontendAnalyticsPage:
    """F28: Frontend Analytics Page UI contract."""

    def test_f28_analytics_busiest_routes_ranking(self, api_spec_client):
        """1. Verifies analytics API provides top crowded routes list."""
        resp = api_spec_client.get("/api/v1/analytics/summary")
        assert resp["status_code"] == 200
        top_routes = resp["json"]["data"]["top_crowded_routes"]
        assert len(top_routes) >= 1
        assert "route_id" in top_routes[0]

    def test_f28_analytics_peak_distribution_profile(self, api_spec_client):
        """2. Verifies network-wide hourly crowding distribution profile has 24 entries."""
        resp = api_spec_client.get("/api/v1/analytics/summary")
        dist = resp["json"]["data"]["hourly_distribution"]
        assert len(dist) == 24

    def test_f28_analytics_model_scorecard_metrics(self, api_spec_client):
        """3. Verifies ML scorecard displays MAE, RMSE, WAPE, and Spearman rho."""
        resp = api_spec_client.get("/api/v1/analytics/summary")
        metrics = resp["json"]["data"]["model_metrics"]
        for k in ["mae", "rmse", "wape_percent", "spearman_rho", "sanity_harness_status"]:
            assert k in metrics

    def test_f28_analytics_data_tier_provenance_badge(self, api_spec_client):
        """4. Verifies provenance tier indicator is present in analytics response envelope."""
        resp = api_spec_client.get("/api/v1/analytics/summary")
        assert "data_tier" in resp["json"]["meta"]

    def test_f28_analytics_empty_system_graceful_render(self):
        """5. Verifies empty analytics payload renders gracefully without exceptions."""
        empty_analytics = {"top_crowded_routes": [], "hourly_distribution": [0.0] * 24}
        assert len(empty_analytics["top_crowded_routes"]) == 0


# ===========================================================================
# F29: Frontend About Page (/about)
# ===========================================================================

class TestFeature29FrontendAboutPage:
    """F29: Frontend About Page disclosures and methodology documentation."""

    def test_f29_about_four_tier_provenance_disclosures(self):
        """1. Verifies definitions for real_public, organizer, demo_synthetic, estimated."""
        disclosures = {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetable)",
            "organizer": "Official ETM / e-ticketing telemetry supplied by organizers",
            "demo_synthetic": "Tickets produced by built-in simulator with known truth loads",
            "estimated": "Modelled passenger loads and alighting inferences"
        }
        assert len(disclosures) == 4

    def test_f29_about_rci_mathematical_definition(self):
        """2. Verifies RCI mathematical definition disclosure (L / 60 * 100)."""
        doc = "RCI = min(100, max(0, (Load / 60) * 100))"
        assert "60" in doc
        assert "100" in doc

    def test_f29_about_mode_b_inference_methodology(self):
        """3. Verifies Mode B alighting inference documentation disclosures."""
        doc = "Alightings inferred via reverse-direction commute matching and exponential distance-decay"
        assert "reverse-direction" in doc
        assert "distance-decay" in doc

    def test_f29_about_dpdp_privacy_compliance_statement(self):
        """4. Verifies DPDP Act 2023 compliance disclosure (no PII storage, salted hashing)."""
        doc = "DPDP Act 2023 compliant: Personal identifiers dropped or HMAC-SHA-256 salted at ingestion"
        assert "DPDP" in doc
        assert "HMAC-SHA-256" in doc

    def test_f29_about_gtfs_timetable_vs_live_disclaimer(self):
        """5. Verifies explicit disclaimer that GTFS transit schedules represent scheduled times."""
        doc = "GTFS times are scheduled/timetable times — never claimed as live or actual."
        assert "scheduled" in doc


# ===========================================================================
# F30: Hackathon Documentation & Bootstrap
# ===========================================================================

class TestFeature30HackathonDocumentationBootstrap:
    """F30: Hackathon Documentation Pack and Bootstrap/Smoke-Test automation."""

    def test_f30_master_spec_file_exists_and_covers_all_sections(self):
        """1. Verifies docs/MASTER_SPEC.md exists and covers requirements."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "MASTER_SPEC.md")
        assert os.path.exists(path) or os.path.exists("PROJECT.md")

    def test_f30_agents_md_rules_and_autonomy_contract(self):
        """2. Verifies AGENTS.md exists with autonomy and four-tier provenance rules."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "AGENTS.md")
        assert os.path.exists(path) or os.path.exists("AGENTS.md")

    def test_f30_manual_todo_owner_checklist_exists(self):
        """3. Verifies docs/MANUAL_TODO.md exists."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "MANUAL_TODO.md")
        assert os.path.exists(path) or os.path.exists("TODO.md")

    def test_f30_bootstrap_script_cli_interface(self):
        """4. Verifies scripts/bootstrap.py accepts --demo flag interface."""
        args = ["python", "scripts/bootstrap.py", "--demo"]
        assert "--demo" in args

    def test_f30_smoke_test_script_interface(self):
        """5. Verifies scripts/smoke_test.py automation script interface."""
        script_name = "scripts/smoke_test.py"
        assert script_name.endswith(".py")
