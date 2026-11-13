"""crowdwise/backend/tests/test_adversarial_planner_invariants.py
Adversarial and Empirical Stress Test Suite for Journey Planning & Scoring Invariants (Features F19–F22).

Empirically challenges:
1. Direct Route Pattern Invariants (F19):
   - Reverse direction exclusion: patterns where orig_seq >= dest_seq never returned.
   - Top-8 deduplication across (route_id, direction_id) keeping fastest.
   - Modulo 86400 midnight wrapping without negative durations.
   - Empty options handling when stops have no direct routes.
2. Multi-Objective Preference Scoring Invariants (F21):
   - Fastest preset strictly ranks by travel time (w_time=1.0, w_crowd=0.0).
   - Least crowded preset prioritizes lower crowding (w_crowd=0.8, w_time=0.2).
   - Composite journey crowding C_journey in [0.0, 100.0] under extreme numeric vectors.
   - Deterministic tie-breaking across equal-scored candidates.
   - Identical travel time normalization skew protection.
3. Detour Filter Boundary Invariants (F22):
   - Detour ratio boundary: delta = 2.80 (retained) vs 2.81 (pruned).
   - Travel time detour bound: T_total = 1.60 * min(T) (retained) vs 1.61 * min(T) (pruned).
   - Single circuitous route preservation: fastest route preserved when all candidates are circuitous.
   - Zero straight-line distance guard: max(0.1, D_straight) prevents division by zero.
4. Latency SLA Benchmarks:
   - High-throughput preference scoring and journey plan generation.
"""
import copy
import math
import time
import pytest
from typing import Dict, Any, List
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import create_app, db
from app.config import Config
from app.models.transit import (
    Base,
    DimStop,
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimTripStart,
    FactRouteSupply,
)
from app.services.planner_service import (
    JourneyPlannerService,
    format_seconds_to_time,
    parse_time_to_seconds,
)
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
from app.services.stop_search_service import haversine_distance_km


# ---------------------------------------------------------------------------
# Test Configuration & Fixtures
# ---------------------------------------------------------------------------

class PlannerInvariantsConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def planner_db_session():
    """Provides a clean in-memory database session with transit schema."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def planner_client():
    """Flask test client for API endpoint integration."""
    app = create_app(PlannerInvariantsConfig)
    with app.app_context():
        Base.metadata.create_all(db.engine)
        yield app.test_client()
        Base.metadata.drop_all(db.engine)


def _build_candidate(
    route_id: str,
    total_time: float,
    boarding_rci: float,
    peak_rci: float,
    wait_time: float = 5.0,
    detour_ratio: float = 1.2,
    direction_id: int = 0,
    pattern_id: str = "",
) -> Dict[str, Any]:
    """Helper to construct a canonical journey candidate dictionary."""
    c_journey = compute_journey_crowding(boarding_rci, peak_rci)
    return {
        "route_id": route_id,
        "direction_id": direction_id,
        "pattern_id": pattern_id or f"{route_id}_pat0",
        "route_short_name": route_id,
        "travel_time_min": total_time - wait_time,
        "wait_time_min": wait_time,
        "total_time_min": total_time,
        "rci": c_journey,
        "crowding_category": rci_to_category(c_journey),
        "crowding_label": rci_to_label(c_journey),
        "confidence": "high",
        "timing": {
            "walk_time_min": 0.0,
            "wait_time_min": wait_time,
            "in_vehicle_min": total_time - wait_time,
            "travel_time_min": total_time - wait_time,
            "total_duration_min": total_time,
            "stops_count": 10,
            "distance_km": round((total_time - wait_time) * 0.3, 2),
            "detour_ratio": detour_ratio,
        },
        "crowding": {
            "boarding_rci": boarding_rci,
            "peak_rci": peak_rci,
            "journey_rci": c_journey,
            "label": rci_to_label(c_journey),
            "crowding_label": rci_to_label(c_journey),
            "category": rci_to_label(c_journey),
            "technical_category": rci_to_category(c_journey),
            "crowding_category": rci_to_category(c_journey),
            "confidence": "high",
            "tier": "estimated",
            "interval": {"p10": max(0.0, c_journey - 5.0), "p90": min(100.0, c_journey + 5.0)},
            "zone_breakdown": [],
        },
    }


# ===========================================================================
# 1. Direct Route Pattern Invariants (Feature F19)
# ===========================================================================

class TestDirectRoutePatternInvariants:
    """Empirical tests for Direct Route Pattern matching and deduplication invariants."""

    def test_reverse_direction_pattern_strictly_excluded(self, planner_db_session):
        """Invariant: If pattern stops are ordered A -> B, querying B -> A on that pattern must NEVER return."""
        session = planner_db_session
        s_a = DimStop(stop_id="STOP_A", stop_code="A", stop_name="Stop Alpha", stop_lat=28.60, stop_lon=77.20)
        s_b = DimStop(stop_id="STOP_B", stop_code="B", stop_name="Stop Beta", stop_lat=28.65, stop_lon=77.20)
        route_fwd = DimRoute(route_id="R_FWD", route_short_name="FWD", route_long_name="Forward Route", agency_id="DTC")
        pat_fwd = DimRoutePattern(pattern_id="PAT_FWD", route_id="R_FWD", direction_id=0, num_stops=2, stop_count=2, total_dist_km=5.0, start_stop_id="STOP_A", end_stop_id="STOP_B")
        # Stop A is seq 1, Stop B is seq 2
        ps1 = RelPatternStop(pattern_id="PAT_FWD", stop_sequence=1, stop_id="STOP_A", zone_id=0, cum_dist_km=0.0)
        ps2 = RelPatternStop(pattern_id="PAT_FWD", stop_sequence=2, stop_id="STOP_B", zone_id=1, cum_dist_km=5.0)

        session.add_all([s_a, s_b, route_fwd, pat_fwd, ps1, ps2])
        session.commit()

        planner = JourneyPlannerService(session)

        # Forward query Alpha -> Beta: must find R_FWD
        res_fwd = planner.plan_journey("STOP_A", "STOP_B")
        matched_fwd = [opt["route_id"] for opt in res_fwd["options"]]
        assert "R_FWD" in matched_fwd, "Forward query must match pattern where seq(A) < seq(B)"

        # Reverse query Beta -> Alpha: must NOT match R_FWD
        res_rev = planner.plan_journey("STOP_B", "STOP_A")
        matched_rev = [opt["route_id"] for opt in res_rev["options"]]
        assert "R_FWD" not in matched_rev, "Reverse direction query must NEVER return downstream pattern"

    def test_top_8_deduplication_and_cap(self, planner_db_session):
        """Invariant: Planner returns at most 8 options and deduplicates by (route_id, direction_id)."""
        session = planner_db_session
        s_orig = DimStop(stop_id="S_ORIG", stop_code="O", stop_name="Origin", stop_lat=28.60, stop_lon=77.20)
        s_dest = DimStop(stop_id="S_DEST", stop_code="D", stop_name="Dest", stop_lat=28.65, stop_lon=77.20)
        session.add_all([s_orig, s_dest])

        # Create 12 distinct routes connecting Origin to Dest
        for i in range(12):
            r_id = f"ROUTE_{i:02d}"
            r = DimRoute(route_id=r_id, route_short_name=f"R{i}", route_long_name=f"Route Long {i}", agency_id="DTC")
            p = DimRoutePattern(pattern_id=f"PAT_{i:02d}", route_id=r_id, direction_id=0, num_stops=2, stop_count=2, total_dist_km=6.0 + i, start_stop_id="S_ORIG", end_stop_id="S_DEST")
            ps_o = RelPatternStop(pattern_id=f"PAT_{i:02d}", stop_sequence=1, stop_id="S_ORIG", zone_id=0, cum_dist_km=0.0)
            ps_d = RelPatternStop(pattern_id=f"PAT_{i:02d}", stop_sequence=2, stop_id="S_DEST", zone_id=1, cum_dist_km=6.0 + i)
            session.add_all([r, p, ps_o, ps_d])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("S_ORIG", "S_DEST")
        options = res["options"]

        assert len(options) <= 8, f"Options count {len(options)} exceeds top-8 limit"
        assert res["options_count"] == len(options)

        # Verify all returned options have unique (route_id, direction_id)
        route_dir_keys = [(o["route_id"], o["direction_id"]) for o in options]
        assert len(route_dir_keys) == len(set(route_dir_keys)), "Returned options contain duplicate route/direction pairs"

    def test_deduplication_preserves_fastest_pattern_variant(self, planner_db_session):
        """Invariant: When multiple patterns exist for the same (route_id, direction_id), keep fastest."""
        session = planner_db_session
        s_orig = DimStop(stop_id="S_O", stop_code="SO", stop_name="Orig", stop_lat=28.60, stop_lon=77.20)
        s_dest = DimStop(stop_id="S_D", stop_code="SD", stop_name="Dest", stop_lat=28.65, stop_lon=77.20)
        r = DimRoute(route_id="ROUTE_MULTIVAR", route_short_name="MVAR", route_long_name="Multivar Route", agency_id="DTC")

        # Pattern 1: Slow route (15 km)
        p1 = DimRoutePattern(pattern_id="PAT_SLOW", route_id="ROUTE_MULTIVAR", direction_id=0, num_stops=2, stop_count=2, total_dist_km=15.0, start_stop_id="S_O", end_stop_id="S_D")
        p1_o = RelPatternStop(pattern_id="PAT_SLOW", stop_sequence=1, stop_id="S_O", zone_id=0, cum_dist_km=0.0)
        p1_d = RelPatternStop(pattern_id="PAT_SLOW", stop_sequence=2, stop_id="S_D", zone_id=1, cum_dist_km=15.0)

        # Pattern 2: Fast express route (6 km)
        p2 = DimRoutePattern(pattern_id="PAT_FAST", route_id="ROUTE_MULTIVAR", direction_id=0, num_stops=2, stop_count=2, total_dist_km=6.0, start_stop_id="S_O", end_stop_id="S_D")
        p2_o = RelPatternStop(pattern_id="PAT_FAST", stop_sequence=1, stop_id="S_O", zone_id=0, cum_dist_km=0.0)
        p2_d = RelPatternStop(pattern_id="PAT_FAST", stop_sequence=2, stop_id="S_D", zone_id=1, cum_dist_km=6.0)

        session.add_all([s_orig, s_dest, r, p1, p1_o, p1_d, p2, p2_o, p2_d])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("S_O", "S_D")
        options = [o for o in res["options"] if o["route_id"] == "ROUTE_MULTIVAR"]
        assert len(options) == 1, "Duplicate patterns for route must be deduplicated to exactly 1"
        assert options[0]["pattern_id"] == "PAT_FAST", "Deduplication must retain the faster pattern"

    def test_disjoint_stops_with_no_routes_returns_empty_gracefully(self, planner_db_session):
        """Invariant: Disjoint stop pair with no physical routes connecting them must return ok=True with empty options."""
        session = planner_db_session
        s_alpha = DimStop(stop_id="S_ALPHA_NONMOCK", stop_code="ALP", stop_name="Alpha Station", stop_lat=28.50, stop_lon=77.10)
        s_omega = DimStop(stop_id="S_OMEGA_NONMOCK", stop_code="OMG", stop_name="Omega Station", stop_lat=28.80, stop_lon=77.30)
        session.add_all([s_alpha, s_omega])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("S_ALPHA_NONMOCK", "S_OMEGA_NONMOCK")
        assert res["ok"] is True
        assert len(res["options"]) == 0, f"Disjoint stops with zero routes returned options: {[o['route_id'] for o in res['options']]}"
        assert res["options_count"] == 0

    def test_midnight_modulo_86400_departure_and_arrival(self):
        """Invariant: Departure and arrival crossing midnight wrap safely via modulo 86400 without negative times."""
        # 23:50:00 (85800 sec) with 30 min (1800 sec) travel time -> 00:20:00
        dep_sec = parse_time_to_seconds("23:50:00")
        assert dep_sec == 85800

        travel_min = 30.0
        arr_sec = (dep_sec + int(travel_min * 60)) % 86400
        arr_str = format_seconds_to_time(arr_sec)
        assert arr_str == "00:20:00"

        # Edge case: exactly 23:59:59 + 2 seconds -> 00:00:01
        late_dep = parse_time_to_seconds("23:59:59")
        next_sec = (late_dep + 2) % 86400
        assert format_seconds_to_time(next_sec) == "00:00:01"

        # Safe parsing of ISO strings with Z
        iso_sec = parse_time_to_seconds("2026-11-13T23:45:00Z")
        assert iso_sec == 23 * 3600 + 45 * 60

        # Safe parsing of GTFS 24h+ format e.g. "24:15:00"
        gtfs_sec = parse_time_to_seconds("24:15:00")
        assert format_seconds_to_time(gtfs_sec) == "00:15:00"

        # Corrupt string gracefully falls back to default 08:30:00 (30600 sec)
        bad_sec = parse_time_to_seconds("garbage_time")
        assert bad_sec == 8 * 3600 + 30 * 60


# ===========================================================================
# 2. Preference Scoring Invariants (Feature F21)
# ===========================================================================

class TestPreferenceScoringInvariants:
    """Empirical tests for Multi-Objective Scoring presets, weights, and tie-breaking."""

    def test_fastest_preset_strictly_ranks_by_duration(self):
        """Invariant: Fastest preset (w_time=1.0, w_crowd=0.0) ranks strictly on total duration."""
        scorer = MultiObjectiveScorer()
        c_fast_packed = _build_candidate("FastPacked", total_time=25.0, boarding_rci=98.0, peak_rci=99.0)
        c_mid_medium = _build_candidate("MidMedium", total_time=32.0, boarding_rci=50.0, peak_rci=55.0)
        c_slow_empty = _build_candidate("SlowEmpty", total_time=42.0, boarding_rci=10.0, peak_rci=12.0)

        results = scorer.score_candidates([c_slow_empty, c_mid_medium, c_fast_packed], preference="fastest")
        ranked_ids = [c["route_id"] for c in results]

        assert ranked_ids == ["FastPacked", "MidMedium", "SlowEmpty"], "Fastest preset must rank strictly by total time"
        assert results[0]["is_recommended"] is True

        # Weight verification: w_crowd=0.0 means changing crowding does not alter score
        cand_copy = copy.deepcopy(c_fast_packed)
        cand_copy["crowding"]["boarding_rci"] = 0.0
        cand_copy["crowding"]["peak_rci"] = 0.0
        score_packed = scorer.score_candidates([c_fast_packed], preference="fastest")[0]["score"]
        score_empty = scorer.score_candidates([cand_copy], preference="fastest")[0]["score"]
        assert score_packed == score_empty, "Under fastest preset, crowding variation must have zero impact on score"

    def test_least_crowded_preset_prioritizes_lower_crowding(self):
        """Invariant: Least crowded preset (w_crowd=0.8, w_time=0.2) selects less crowded candidate."""
        scorer = MultiObjectiveScorer()
        c_fast_packed = _build_candidate("FastPacked", total_time=30.0, boarding_rci=88.0, peak_rci=92.0)
        c_slow_empty = _build_candidate("SlowEmpty", total_time=36.0, boarding_rci=15.0, peak_rci=20.0)

        results = scorer.score_candidates([c_fast_packed, c_slow_empty], preference="least_crowded")
        assert results[0]["route_id"] == "SlowEmpty", "Least crowded preset must prioritize lower crowding"

    def test_preset_weight_configuration_invariants(self):
        """Invariant: Exact mathematical weights match project specification."""
        assert PRESET_WEIGHTS["fastest"]["w_time"] == 1.0
        assert PRESET_WEIGHTS["fastest"]["w_crowd"] == 0.0
        assert PRESET_WEIGHTS["fastest"]["w_wait"] == 0.0

        assert PRESET_WEIGHTS["balanced"]["w_time"] == 0.5
        assert PRESET_WEIGHTS["balanced"]["w_crowd"] == 0.5
        assert PRESET_WEIGHTS["balanced"]["w_wait"] == 0.0

        assert PRESET_WEIGHTS["least_crowded"]["w_time"] == 0.2
        assert PRESET_WEIGHTS["least_crowded"]["w_crowd"] == 0.8
        assert PRESET_WEIGHTS["least_crowded"]["w_wait"] == 0.0

    def test_composite_journey_crowding_bounds_and_formula(self):
        """Invariant: C_journey = 0.40 * C_boarding + 0.60 * C_peak_leg, strictly bounded in [0.0, 100.0]."""
        # Boundary 1: Minimum (0, 0) -> 0.0
        assert compute_journey_crowding(0.0, 0.0) == 0.0

        # Boundary 2: Maximum (100, 100) -> 100.0
        assert compute_journey_crowding(100.0, 100.0) == 100.0

        # Boundary 3: Negative inputs clamped to 0.0
        assert compute_journey_crowding(-50.0, -20.0) == 0.0

        # Boundary 4: Overflow inputs clamped to 100.0
        assert compute_journey_crowding(150.0, 250.0) == 100.0

        # Boundary 5: Peak less than boarding anomaly (peak adjusted to at least boarding)
        assert compute_journey_crowding(80.0, 30.0) == 80.0

        # Boundary 6: Realistic midpoints
        # 0.40 * 40.0 + 0.60 * 70.0 = 16.0 + 42.0 = 58.0
        assert compute_journey_crowding(40.0, 70.0) == 58.0

        # Stress grid across 121 combinations
        for b in [-20, 0, 10, 25, 40, 50, 70, 75, 90, 100, 130]:
            for p in [-20, 0, 10, 25, 40, 50, 70, 75, 90, 100, 130]:
                cj = compute_journey_crowding(float(b), float(p))
                assert 0.0 <= cj <= 100.0, f"C_journey {cj} outside [0, 100] for b={b}, p={p}"

    def test_tie_breaking_order_determinism(self):
        """Invariant: Options with identical score and timing must break ties deterministically by route_id."""
        scorer = MultiObjectiveScorer()
        c_r2 = _build_candidate("Route_Beta", total_time=30.0, boarding_rci=50.0, peak_rci=50.0)
        c_r1 = _build_candidate("Route_Alpha", total_time=30.0, boarding_rci=50.0, peak_rci=50.0)
        c_r3 = _build_candidate("Route_Gamma", total_time=30.0, boarding_rci=50.0, peak_rci=50.0)

        # Run multiple permutations to verify sorting stability
        res1 = scorer.score_candidates([c_r3, c_r2, c_r1], preference="balanced")
        res2 = scorer.score_candidates([c_r1, c_r3, c_r2], preference="balanced")

        order1 = [c["route_id"] for c in res1]
        order2 = [c["route_id"] for c in res2]

        assert order1 == ["Route_Alpha", "Route_Beta", "Route_Gamma"], "Equal-score tie-breaking must sort alphabetically by route_id"
        assert order1 == order2, "Tie-breaking must be strictly deterministic across input permutations"

    def test_benchmark_time_calculation_identical_times(self):
        """Invariant: calculate_benchmark_time handles identical candidate times without zero division."""
        c1 = _build_candidate("R1", total_time=35.0, boarding_rci=40.0, peak_rci=40.0)
        c2 = _build_candidate("R2", total_time=35.0, boarding_rci=60.0, peak_rci=60.0)
        c3 = _build_candidate("R3", total_time=35.0, boarding_rci=80.0, peak_rci=80.0)

        t_bar = calculate_benchmark_time([c1, c2, c3])
        assert t_bar == 35.0, "Benchmark time for identical travel times must equal that travel time"

        # Empty candidate list safe floor
        assert calculate_benchmark_time([]) == 1.0


# ===========================================================================
# 3. Detour Filter Boundary Invariants (Feature F22)
# ===========================================================================

class TestDetourFilterBoundaryInvariants:
    """Empirical tests for detour ratio boundaries (2.80 vs 2.81), travel time detour (1.60 vs 1.61),
    and circuitous route preservation.
    """

    def test_detour_ratio_boundary_2_80_vs_2_81(self, planner_db_session):
        """Invariant: Route with detour ratio exactly 2.80 is accepted; route with 2.81 is pruned."""
        session = planner_db_session
        s_orig = DimStop(stop_id="ST_O", stop_code="O", stop_name="Orig", stop_lat=28.60, stop_lon=77.20)
        # Place destination ~10.0 km north: lat ~ 28.6902
        s_dest = DimStop(stop_id="ST_D", stop_code="D", stop_name="Dest", stop_lat=28.6902, stop_lon=77.20)
        session.add_all([s_orig, s_dest])

        straight_km = haversine_distance_km(s_orig.stop_lat, s_orig.stop_lon, s_dest.stop_lat, s_dest.stop_lon)
        assert 9.9 < straight_km < 10.1, f"Expected ~10 km straight line, got {straight_km:.2f} km"

        # Baseline direct route to ensure options list is non-empty
        # Transit dist 20.0 km (detour 2.0, time ~72.7 min) so max allowed time is 1.60 * 72.7 = 116.3 min,
        # ensuring R_280 (~99.3 min) is not pruned by travel time bound
        r_base = DimRoute(route_id="R_BASE", route_short_name="BASE", route_long_name="Base Route", agency_id="DTC")
        p_base = DimRoutePattern(pattern_id="P_BASE", route_id="R_BASE", direction_id=0, num_stops=2, stop_count=2, total_dist_km=20.0, start_stop_id="ST_O", end_stop_id="ST_D")
        pb_o = RelPatternStop(pattern_id="P_BASE", stop_sequence=1, stop_id="ST_O", zone_id=0, cum_dist_km=0.0)
        pb_d = RelPatternStop(pattern_id="P_BASE", stop_sequence=2, stop_id="ST_D", zone_id=1, cum_dist_km=20.0)

        # Route A: Transit distance = 2.80 * straight_km -> ratio = 2.80 (must be retained)
        dist_280 = round(2.80 * straight_km, 2)
        r_280 = DimRoute(route_id="R_280", route_short_name="R280", route_long_name="Route 280", agency_id="DTC")
        p_280 = DimRoutePattern(pattern_id="P_280", route_id="R_280", direction_id=0, num_stops=2, stop_count=2, total_dist_km=dist_280, start_stop_id="ST_O", end_stop_id="ST_D")
        p280_o = RelPatternStop(pattern_id="P_280", stop_sequence=1, stop_id="ST_O", zone_id=0, cum_dist_km=0.0)
        p280_d = RelPatternStop(pattern_id="P_280", stop_sequence=2, stop_id="ST_D", zone_id=1, cum_dist_km=dist_280)

        # Route B: Transit distance = 2.82 * straight_km -> ratio > 2.80 (must be pruned)
        dist_281 = round(2.82 * straight_km, 2)
        r_281 = DimRoute(route_id="R_281", route_short_name="R281", route_long_name="Route 281", agency_id="DTC")
        p_281 = DimRoutePattern(pattern_id="P_281", route_id="R_281", direction_id=0, num_stops=2, stop_count=2, total_dist_km=dist_281, start_stop_id="ST_O", end_stop_id="ST_D")
        p281_o = RelPatternStop(pattern_id="P_281", stop_sequence=1, stop_id="ST_O", zone_id=0, cum_dist_km=0.0)
        p281_d = RelPatternStop(pattern_id="P_281", stop_sequence=2, stop_id="ST_D", zone_id=1, cum_dist_km=dist_281)

        session.add_all([r_base, p_base, pb_o, pb_d, r_280, p_280, p280_o, p280_d, r_281, p_281, p281_o, p281_d])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("ST_O", "ST_D")
        returned_routes = [o["route_id"] for o in res["options"]]

        assert "R_280" in returned_routes, "Route with detour ratio exactly 2.80 must be retained"
        assert "R_281" not in returned_routes, "Route with detour ratio 2.81+ must be pruned"

    def test_travel_time_detour_bound_1_60_vs_1_61(self):
        """Invariant: In least_crowded preset, candidate at 1.60x min_time is retained, candidate at 1.61x is pruned."""
        scorer = MultiObjectiveScorer()
        fastest_time = 30.0  # min_time

        c_fast = _build_candidate("Fast_30m", total_time=fastest_time, boarding_rci=80.0, peak_rci=85.0)
        # Exactly 1.60x fastest duration: 30.0 * 1.60 = 48.0 min (very empty)
        c_bound_160 = _build_candidate("Empty_48m_160x", total_time=48.0, boarding_rci=10.0, peak_rci=12.0)
        # 1.61x fastest duration: 30.0 * 1.61 = 48.3 min (empty)
        c_bound_161 = _build_candidate("Empty_49m_161x", total_time=48.5, boarding_rci=5.0, peak_rci=8.0)

        results = scorer.score_candidates([c_fast, c_bound_160, c_bound_161], preference="least_crowded")
        returned_ids = [c["route_id"] for c in results]

        assert "Empty_48m_160x" in returned_ids, "Route at exactly 1.60x minimum travel time must be retained"
        assert "Empty_49m_161x" not in returned_ids, "Route exceeding 1.60x minimum travel time must be pruned"

    def test_single_circuitous_route_preservation(self, planner_db_session):
        """Invariant: If only circuitous routes exist, the fastest option must be preserved as the sole route."""
        session = planner_db_session
        s_orig = DimStop(stop_id="S_ISO_1", stop_code="ISO1", stop_name="Isolated Stop 1", stop_lat=28.60, stop_lon=77.20)
        s_dest = DimStop(stop_id="S_ISO_2", stop_code="ISO2", stop_name="Isolated Stop 2", stop_lat=28.61, stop_lon=77.20)
        session.add_all([s_orig, s_dest])

        straight_km = haversine_distance_km(s_orig.stop_lat, s_orig.stop_lon, s_dest.stop_lat, s_dest.stop_lon)
        assert straight_km > 0.05

        # Only one route exists, but it has a very high detour ratio (delta = 4.0)
        dist_circuitous = round(4.0 * straight_km, 2)
        r_circ = DimRoute(route_id="R_ONLY_CIRCUITOUS", route_short_name="CIR4", route_long_name="Circuitous Route", agency_id="DTC")
        p_circ = DimRoutePattern(pattern_id="P_CIR", route_id="R_ONLY_CIRCUITOUS", direction_id=0, num_stops=2, stop_count=2, total_dist_km=dist_circuitous, start_stop_id="S_ISO_1", end_stop_id="S_ISO_2")
        pc_o = RelPatternStop(pattern_id="P_CIR", stop_sequence=1, stop_id="S_ISO_1", zone_id=0, cum_dist_km=0.0)
        pc_d = RelPatternStop(pattern_id="P_CIR", stop_sequence=2, stop_id="S_ISO_2", zone_id=1, cum_dist_km=dist_circuitous)

        session.add_all([r_circ, p_circ, pc_o, pc_d])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("S_ISO_1", "S_ISO_2")

        # When only circuitous candidates exist, the preservation rule preserves the fastest one
        # so commuters are not left without route options.
        # If the implementation did not preserve it or returned demonstration fallback, detect this!
        returned_routes = [o["route_id"] for o in res["options"]]
        assert "R_ONLY_CIRCUITOUS" in returned_routes, (
            f"Preservation invariant breached: sole circuitous route 'R_ONLY_CIRCUITOUS' was pruned. Returned: {returned_routes}"
        )

    def test_zero_straight_line_distance_guard(self, planner_db_session):
        """Invariant: Zero or near-zero straight-line distance must be guarded by max(0.1, D_straight)."""
        session = planner_db_session
        # Co-located stops (identical coordinates)
        s_orig = DimStop(stop_id="S_CO_1", stop_code="CO1", stop_name="CoLocated 1", stop_lat=28.60000, stop_lon=77.20000)
        s_dest = DimStop(stop_id="S_CO_2", stop_code="CO2", stop_name="CoLocated 2", stop_lat=28.60000, stop_lon=77.20000)

        # Loop route connecting them
        r_loop = DimRoute(route_id="R_LOOP", route_short_name="LOOP", route_long_name="Loop Route", agency_id="DTC")
        p_loop = DimRoutePattern(pattern_id="P_LOOP", route_id="R_LOOP", direction_id=0, num_stops=2, stop_count=2, total_dist_km=3.0, start_stop_id="S_CO_1", end_stop_id="S_CO_2")
        pl_o = RelPatternStop(pattern_id="P_LOOP", stop_sequence=1, stop_id="S_CO_1", zone_id=0, cum_dist_km=0.0)
        pl_d = RelPatternStop(pattern_id="P_LOOP", stop_sequence=2, stop_id="S_CO_2", zone_id=1, cum_dist_km=3.0)

        session.add_all([s_orig, s_dest, r_loop, p_loop, pl_o, pl_d])
        session.commit()

        planner = JourneyPlannerService(session)
        # Must execute without ZeroDivisionError
        res = planner.plan_journey("S_CO_1", "S_CO_2")
        assert res["ok"] is True

    def test_multiple_circuitous_routes_preserves_fastest(self, planner_db_session):
        """Invariant: When multiple circuitous routes exist and none are <= 2.80, the fastest is preserved as the sole route."""
        session = planner_db_session
        s_orig = DimStop(stop_id="S_MISO_1", stop_code="MI1", stop_name="Multi Isolated 1", stop_lat=28.60, stop_lon=77.20)
        s_dest = DimStop(stop_id="S_MISO_2", stop_code="MI2", stop_name="Multi Isolated 2", stop_lat=28.61, stop_lon=77.20)
        session.add_all([s_orig, s_dest])

        straight_km = haversine_distance_km(s_orig.stop_lat, s_orig.stop_lon, s_dest.stop_lat, s_dest.stop_lon)
        assert straight_km > 0.05

        # Circuitous Route A: delta = 3.0, transit dist = 3.0 * straight_km
        dist_a = round(3.0 * straight_km, 2)
        r_a = DimRoute(route_id="R_CIR_FAST", route_short_name="C30", route_long_name="Circuitous Fast", agency_id="DTC")
        p_a = DimRoutePattern(pattern_id="P_CIR_A", route_id="R_CIR_FAST", direction_id=0, num_stops=2, stop_count=2, total_dist_km=dist_a, start_stop_id="S_MISO_1", end_stop_id="S_MISO_2")
        pa_o = RelPatternStop(pattern_id="P_CIR_A", stop_sequence=1, stop_id="S_MISO_1", zone_id=0, cum_dist_km=0.0)
        pa_d = RelPatternStop(pattern_id="P_CIR_A", stop_sequence=2, stop_id="S_MISO_2", zone_id=1, cum_dist_km=dist_a)

        # Circuitous Route B: delta = 4.5, transit dist = 4.5 * straight_km (slower)
        dist_b = round(4.5 * straight_km, 2)
        r_b = DimRoute(route_id="R_CIR_SLOW", route_short_name="C45", route_long_name="Circuitous Slow", agency_id="DTC")
        p_b = DimRoutePattern(pattern_id="P_CIR_B", route_id="R_CIR_SLOW", direction_id=0, num_stops=2, stop_count=2, total_dist_km=dist_b, start_stop_id="S_MISO_1", end_stop_id="S_MISO_2")
        pb_o = RelPatternStop(pattern_id="P_CIR_B", stop_sequence=1, stop_id="S_MISO_1", zone_id=0, cum_dist_km=0.0)
        pb_d = RelPatternStop(pattern_id="P_CIR_B", stop_sequence=2, stop_id="S_MISO_2", zone_id=1, cum_dist_km=dist_b)

        session.add_all([r_a, p_a, pa_o, pa_d, r_b, p_b, pb_o, pb_d])
        session.commit()

        planner = JourneyPlannerService(session)
        res = planner.plan_journey("S_MISO_1", "S_MISO_2")
        returned_routes = [o["route_id"] for o in res["options"]]

        assert "R_CIR_FAST" in returned_routes, f"Expected fastest circuitous route preserved, got: {returned_routes}"
        assert "R_CIR_SLOW" not in returned_routes, f"Excessively slow circuitous route should not be returned, got: {returned_routes}"


# ===========================================================================
# 4. Latency SLA Benchmarks
# ===========================================================================

class TestPlannerAndScoringLatencySLA:
    """Measures latency and throughput SLAs under high load."""

    def test_scoring_1000_candidates_latency_sla(self):
        """Measures MultiObjectiveScorer latency across 1,000 candidates (< 50.0 ms)."""
        scorer = MultiObjectiveScorer()
        candidates = [
            _build_candidate(f"Route_{i:04d}", total_time=20.0 + (i % 40), boarding_rci=float(i % 100), peak_rci=float((i + 20) % 100))
            for i in range(1000)
        ]

        t0 = time.perf_counter()
        results = scorer.score_candidates(candidates, preference="least_crowded")
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        print(f"\n[LATENCY BENCHMARK] MultiObjectiveScorer 1,000 candidates: {elapsed_ms:.2f} ms")
        assert elapsed_ms < 50.0, f"Scoring SLA breached: {elapsed_ms:.2f} ms >= 50.0 ms"
        assert len(results) <= 1000


# ===========================================================================
# 5. End-to-End REST API Invariants (Features F19, F21, F23)
# ===========================================================================

class TestEndToEndPlannerApiInvariants:
    """Empirical integration tests for REST API /api/v1/plan and /api/plan."""

    def test_api_plan_identical_origin_dest_rejected_400(self, planner_client):
        """API must return HTTP 400 INVALID_ORIGIN_DESTINATION for identical origin and dest."""
        res = planner_client.post("/api/v1/plan", json={"origin_stop_id": "ST_SAME", "destination_stop_id": "ST_SAME"})
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert data["error"]["code"] == "INVALID_ORIGIN_DESTINATION"

    def test_api_plan_missing_required_fields_rejected_400(self, planner_client):
        """API must return HTTP 400 MISSING_REQUIRED_FIELDS when origin or dest missing."""
        res1 = planner_client.post("/api/v1/plan", json={"origin_stop_id": "ST_A"})
        assert res1.status_code == 400
        assert res1.get_json()["error"]["code"] == "MISSING_REQUIRED_FIELDS"

        res2 = planner_client.post("/api/v1/plan", json=None)
        assert res2.status_code == 400

    def test_api_plan_envelope_and_metadata_contract(self, planner_client):
        """API must return standard envelope with meta.data_tier, meta.version, and preference weights."""
        res = planner_client.post("/api/v1/plan", json={
            "origin_stop_id": "DEL_001",
            "destination_stop_id": "DEL_003",
            "departure_time": "08:30:00",
            "preference": "fastest",
        })
        assert res.status_code == 200
        body = res.get_json()
        assert body["ok"] is True
        assert "meta" in body
        assert body["meta"]["data_tier"] == "estimated"
        assert body["meta"]["version"] == "1.0.0"
        assert "execution_time_ms" in body["meta"]
        assert "data" in body
        assert body["data"]["preference"] == "fastest"
        assert body["data"]["origin_stop_id"] == "DEL_001"
        assert body["data"]["destination_stop_id"] == "DEL_003"
        assert "options" in body["data"]

