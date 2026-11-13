"""crowdwise/backend/tests/test_adversarial_demand_invariants.py
Adversarial Stress-Testing Suite for Demand Reconstruction Invariants (Milestone M2: F07, F08, F09, 8-Zone).
Executed by Challenger M2.1 to stress-test mathematical correctness and physical invariants.
"""
import math
import random
import pytest
import numpy as np
import pandas as pd
from typing import List, Dict, Any

from app.demand.alighting_model import ModeBAlightingInferenceEngine
from app.demand.reconstruction import ModeAReconstructor, ModeCDisaggregator, ZoneDemandAggregator


# ===========================================================================
# 1. MODE A DIRECT OD ADVERSARIAL STRESS SUITE (F07)
# ===========================================================================

class TestAdversarialModeA:
    """Adversarial stress-testing of Mode A Direct OD Reconstruction."""

    def test_mode_a_strict_conservation_and_clearance_randomized(self):
        """Stress-test with 500 randomized trips of various lengths (N=3 to 60) and 1000s of tickets."""
        rng = random.Random(42)
        reconstructor = ModeAReconstructor()

        for trip_idx in range(500):
            N = rng.randint(3, 60)
            pattern_stops = [(s, f"STOP_{s:03d}", s // 8, float(s * 1.5)) for s in range(N)]
            
            # Generate random tickets
            num_tickets = rng.randint(10, 200)
            tickets = []
            for _ in range(num_tickets):
                orig = rng.randint(0, N - 1)
                dest = rng.randint(0, N - 1)
                pax = rng.randint(1, 10)
                tickets.append({
                    "boarding_stop_id": f"STOP_{orig:03d}",
                    "alighting_stop_id": f"STOP_{dest:03d}",
                    "passenger_count": pax,
                })

            res = reconstructor.reconstruct_trip(pattern_stops, tickets)
            boardings = res["boardings"]
            alightings = res["alightings"]
            loads = res["loads"]

            # Invariant 1: Strict load conservation (total boardings == total alightings)
            total_b = sum(boardings)
            total_a = sum(alightings)
            assert total_b == pytest.approx(total_a, abs=1e-7), (
                f"Trip {trip_idx}: Total boardings ({total_b}) != total alightings ({total_a})"
            )

            # Invariant 2: Non-negativity at every stop
            for s in range(N):
                assert loads[s] >= 0.0, f"Trip {trip_idx}: Negative load {loads[s]} at stop {s}"

            # Invariant 3: Terminal clearance
            assert loads[-1] == 0.0, f"Trip {trip_idx}: Terminal load {loads[-1]} != 0.0"

    def test_mode_a_pathological_edge_cases(self):
        """Adversarial inputs: empty tickets, all same-stop, reverse tickets, non-existent stops."""
        reconstructor = ModeAReconstructor()
        pattern_stops = [(s, f"STOP_{s}", s // 2, float(s)) for s in range(10)]
        N = len(pattern_stops)

        # 1. Empty tickets list
        res_empty = reconstructor.reconstruct_trip(pattern_stops, [])
        assert sum(res_empty["boardings"]) == 0.0
        assert sum(res_empty["alightings"]) == 0.0
        assert res_empty["loads"] == [0.0] * N

        # 2. Same-stop journeys (orig == dest)
        same_stop_tickets = [{"boarding_stop_id": f"STOP_{s}", "alighting_stop_id": f"STOP_{s}", "passenger_count": 5} for s in range(N)]
        res_same = reconstructor.reconstruct_trip(pattern_stops, same_stop_tickets)
        assert sum(res_same["boardings"]) == 0.0
        assert sum(res_same["alightings"]) == 0.0
        assert all(l == 0.0 for l in res_same["loads"])

        # 3. Reverse-direction tickets (orig > dest) on a forward trip
        rev_tickets = [
            {"boarding_stop_id": "STOP_8", "alighting_stop_id": "STOP_2", "passenger_count": 10},
            {"boarding_stop_id": "STOP_5", "alighting_stop_id": "STOP_1", "passenger_count": 7},
        ]
        res_rev = reconstructor.reconstruct_trip(pattern_stops, rev_tickets)
        assert sum(res_rev["boardings"]) == 0.0
        assert sum(res_rev["alightings"]) == 0.0
        assert all(l == 0.0 for l in res_rev["loads"])

        # 4. Unknown/malformed stops
        unknown_tickets = [
            {"boarding_stop_id": "GHOST_STOP", "alighting_stop_id": "STOP_5", "passenger_count": 3},
            {"boarding_stop_id": "STOP_2", "alighting_stop_id": "NOWHERE", "passenger_count": 4},
        ]
        res_unknown = reconstructor.reconstruct_trip(pattern_stops, unknown_tickets)
        assert sum(res_unknown["boardings"]) == 0.0
        assert res_unknown["unmatched_tickets"] == 2


# ===========================================================================
# 2. MODE B ALIGHTING INFERENCE ADVERSARIAL STRESS SUITE (F08)
# ===========================================================================

class TestAdversarialModeB:
    """Adversarial stress-testing of Mode B Hybrid Alighting Inference Engine."""

    def test_mode_b_probability_distribution_normalization_exhaustive(self):
        """Verify sum(P(j | i)) == 1.0 (within 1e-4) for all boarding stops i < N-1 across diverse pattern sizes."""
        engine = ModeBAlightingInferenceEngine()
        rng = random.Random(123)

        for N in [3, 4, 8, 15, 30, 75]:
            pattern_stops = [(s, f"S_{s}", min(7, s * 8 // N), float(s * 1.2)) for s in range(N)]
            
            # Test under 4 reverse boarding regimes:
            # a) Zero reverse
            # b) Uniform reverse
            # c) Sparse single-hub reverse
            # d) Heavy random reverse
            regimes = [
                {},
                {s: 10 for s in range(N)},
                {N - 1: 500},
                {s: rng.randint(0, 100) for s in range(N)},
            ]

            for rev in regimes:
                for boarding_idx in range(N - 1):
                    probs = engine.compute_alighting_probabilities(
                        pattern_stops=pattern_stops,
                        boarding_idx=boarding_idx,
                        reverse_boardings=rev,
                    )
                    
                    # Must contain only downstream stops
                    assert all(j > boarding_idx for j in probs.keys())
                    assert all(j < N for j in probs.keys())

                    # Sum of probabilities must normalize to 1.0
                    prob_sum = sum(probs.values())
                    assert prob_sum == pytest.approx(1.0, abs=1e-4), (
                        f"N={N}, b_idx={boarding_idx}: Probabilities sum to {prob_sum} != 1.0"
                    )

    def test_mode_b_penultimate_certainty_invariant(self):
        """At stop N-2, P(N-1 | N-2) MUST BE 1.0 under all adverse reverse patterns and distances."""
        engine = ModeBAlightingInferenceEngine()

        for N in [2, 3, 5, 20, 50]:
            # Degenerate & extreme reverse patterns
            for rev_val in [0, 1, 1000000]:
                for dist_delta in [0.001, 1.0, 500.0]:
                    pattern_stops = [
                        (s, f"S_{s}", 0, float(s * dist_delta)) for s in range(N)
                    ]
                    probs = engine.compute_alighting_probabilities(
                        pattern_stops=pattern_stops,
                        boarding_idx=N - 2,
                        reverse_boardings={N - 1: rev_val},
                    )
                    assert N - 1 in probs
                    assert probs[N - 1] == 1.0, f"Penultimate certainty failed: {probs}"
                    assert len(probs) == 1

    def test_mode_b_reverse_weight_scaling_and_fallback(self):
        """Verify dynamic blend weight alpha:
        - 0 reverse obs -> alpha = 0.0 (pure distance decay)
        - 25 reverse obs -> alpha = 0.50
        - 50 reverse obs -> alpha = 0.75
        - 10,000 reverse obs -> alpha capped at 0.75
        """
        engine = ModeBAlightingInferenceEngine(alpha_cap=0.75, m_threshold=50.0)
        pattern = [(0, "S0", 0, 0.0), (1, "S1", 1, 2.0), (2, "S2", 2, 4.0), (3, "S3", 3, 6.0)]

        # Zero reverse observations
        probs_pure = engine.compute_alighting_probabilities(pattern, 0, reverse_boardings={})
        probs_zero = engine.compute_alighting_probabilities(pattern, 0, reverse_boardings={1: 0, 2: 0, 3: 0})
        for k in probs_pure:
            assert probs_pure[k] == pytest.approx(probs_zero[k], abs=1e-5)

        # 25 reverse obs -> alpha = 25/50 = 0.50
        probs_mid = engine.compute_alighting_probability(
            boarding_seq=0,
            downstream_seqs=[1, 2, 3],
            reverse_boardings={3: 25},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0},
        )
        probs_mid_override = engine.compute_alighting_probability(
            boarding_seq=0,
            downstream_seqs=[1, 2, 3],
            reverse_boardings={3: 25},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0},
            alpha_override=0.50,
        )
        for k in probs_mid:
            assert probs_mid[k] == pytest.approx(probs_mid_override[k], abs=1e-5)

        # 50 reverse obs -> alpha = 50/50 = 0.75 (since capped at alpha_cap=0.75, or 50/50 = 1.0 -> cap 0.75)
        # Note: eff_alpha = min(0.75, total_rev / 50.0). For 50: min(0.75, 1.0) = 0.75.
        probs_full = engine.compute_alighting_probability(
            boarding_seq=0,
            downstream_seqs=[1, 2, 3],
            reverse_boardings={3: 50},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0},
        )
        probs_full_override = engine.compute_alighting_probability(
            boarding_seq=0,
            downstream_seqs=[1, 2, 3],
            reverse_boardings={3: 50},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0},
            alpha_override=0.75,
        )
        for k in probs_full:
            assert probs_full[k] == pytest.approx(probs_full_override[k], abs=1e-5)

        # 10,000 reverse obs -> alpha capped at 0.75
        probs_cap = engine.compute_alighting_probability(
            boarding_seq=0,
            downstream_seqs=[1, 2, 3],
            reverse_boardings={3: 10000},
            stop_distances_km={0: 0.0, 1: 2.0, 2: 4.0, 3: 6.0},
        )
        for k in probs_cap:
            assert probs_cap[k] == pytest.approx(probs_full_override[k], abs=1e-5)

    def test_mode_b_reconstruction_conservation_and_terminal_clearance_randomized(self):
        """Stress-test 1000 randomized trip reconstructions across varied topologies."""
        engine = ModeBAlightingInferenceEngine()
        rng = random.Random(999)

        for iteration in range(1000):
            N = rng.randint(2, 40)
            pattern_stops = [(s, f"S_{s}", min(7, s * 8 // N), float(s * 1.5)) for s in range(N)]
            
            # Random boardings (including 0 boardings, sparse boardings, heavy boardings)
            boardings = {s: rng.randint(0, 50) for s in range(N)}
            rev_boardings = {s: rng.randint(0, 100) for s in range(N)}

            res = engine.reconstruct_trip(
                pattern_stops=pattern_stops,
                boardings_by_seq=boardings,
                reverse_boardings=rev_boardings,
            )

            b_arr = res["boardings"]
            a_arr = res["alightings"]
            loads = res["loads"]

            total_b = sum(b_arr)
            total_a = sum(a_arr)

            # Invariant 1: Total boardings == total alightings
            assert total_b == pytest.approx(total_a, abs=1e-5), (
                f"Iter {iteration}: Boardings {total_b} != Alightings {total_a}"
            )

            # Invariant 2: Terminal load strictly 0
            assert loads[-1] == 0.0, f"Iter {iteration}: Terminal load {loads[-1]} != 0.0"

            # Invariant 3: Non-negative loads at all stops
            for s in range(N):
                assert loads[s] >= 0.0, f"Iter {iteration}: Negative load {loads[s]} at stop {s}"


# ===========================================================================
# 3. MODE C HARE-NIEMEYER DISAGGREGATION ADVERSARIAL SUITE (F09)
# ===========================================================================

class TestAdversarialModeC:
    """Adversarial stress-testing of Hare-Niemeyer Largest Remainder Disaggregation."""

    @pytest.mark.parametrize("total_passengers", [
        0, 1, 2, 7, 13, 97, 127, 499, 1000, 10007, 73421, 1000000
    ])
    @pytest.mark.parametrize("num_stops", [1, 2, 8, 17, 35, 50])
    def test_hare_niemeyer_exact_integer_conservation(self, total_passengers, num_stops):
        """Stress-test Hare-Niemeyer conservation: sum(allocated) == total_passengers exactly."""
        rng = random.Random(total_passengers + num_stops)
        weights = [rng.uniform(0.01, 100.0) for _ in range(num_stops)]

        allocated = ModeCDisaggregator.disaggregate_hare_niemeyer(total_passengers, weights)

        assert len(allocated) == num_stops
        # Exact integer sum check
        assert sum(allocated) == total_passengers
        # All integers and non-negative
        for x in allocated:
            assert isinstance(x, int)
            assert x >= 0

    def test_hare_niemeyer_degenerate_weights(self):
        """Test zero weights, extreme ratios, and all equal weights."""
        disaggregator = ModeCDisaggregator()

        # 1. All zero weights -> should distribute evenly without crashing
        alloc_zeros = disaggregator.disaggregate_hare_niemeyer(10, [0.0, 0.0, 0.0, 0.0, 0.0])
        assert sum(alloc_zeros) == 10
        assert alloc_zeros == [2, 2, 2, 2, 2]

        # 2. Single non-zero weight -> should receive 100% of demand
        alloc_single = disaggregator.disaggregate_hare_niemeyer(15, [0.0, 1.0, 0.0])
        assert alloc_single == [0, 15, 0]

        # 3. Extreme ratio (1e9 vs 1e-9)
        alloc_extreme = disaggregator.disaggregate_hare_niemeyer(100, [1e9, 1e-9])
        assert alloc_extreme == [100, 0]

    def test_mode_c_trip_reconstruction_terminal_clearance(self):
        """Mode C trip reconstruction must assign 0 boardings to terminal stop and clear load at terminus."""
        disaggregator = ModeCDisaggregator()
        pattern = [(s, f"S_{s}", s // 2, float(s)) for s in range(10)]

        for pax in [1, 10, 100, 5000]:
            res = disaggregator.reconstruct_trip(
                pattern_stops=pattern,
                total_passengers=pax,
            )
            # Terminal stop must have 0 boardings
            assert res["boardings"][-1] == 0.0
            # Total boardings must equal pax
            assert sum(res["boardings"]) == pax
            # Total alightings must equal pax
            assert sum(res["alightings"]) == pytest.approx(pax, abs=1e-5)
            # Terminal load must be 0
            assert res["loads"][-1] == 0.0
            # Non-negativity
            assert all(l >= 0.0 for l in res["loads"])


# ===========================================================================
# 4. 8-ZONE CORRIDOR PARTITION ADVERSARIAL SUITE
# ===========================================================================

class TestAdversarialZonePartition:
    """Adversarial stress-testing of 8-Zone Corridor Partitioning."""

    def test_zone_monotonicity_and_bounds_exhaustive(self):
        """For all route lengths N from 1 to 200, verify zone monotonicity, bounds in [0, 7]."""
        agg = ZoneDemandAggregator()

        for N in range(1, 201):
            zones = [agg.get_zone_for_stop(s, N) for s in range(N)]

            # Invariant 1: Bounds [0, 7]
            assert all(0 <= z <= 7 for z in zones), f"Out of bounds zone in N={N}: {zones}"

            # Invariant 2: Monotonic non-decreasing
            for i in range(len(zones) - 1):
                assert zones[i] <= zones[i + 1], f"Monotonicity violated in N={N}: {zones}"

            # Invariant 3: Anchor at origin
            assert zones[0] == 0, f"Origin stop not in zone 0 for N={N}"

            # Invariant 4: Anchor at terminus for N >= 8
            if N >= 8:
                assert zones[-1] == 7, f"Terminus stop not in zone 7 for N={N}: {zones[-1]}"

    def test_zone_no_gaps_for_n_ge_8(self):
        """For all N >= 8, every zone from 0 to 7 must be covered (no skipped zones)."""
        agg = ZoneDemandAggregator()

        for N in range(8, 150):
            zones = set(agg.get_zone_for_stop(s, N) for s in range(N))
            expected = set(range(8))
            assert zones == expected, f"Gaps detected in N={N}: missing {expected - zones}"


# ===========================================================================
# 5. SPATIAL ZONE DEMAND AGGREGATION INVARIANTS SUITE
# ===========================================================================

class TestAdversarialZoneAggregation:
    """Adversarial stress-testing of spatial zone demand aggregation."""

    def test_zone_aggregation_conservation_and_bounds(self):
        """Stress-test 100 randomized trip zone aggregations for load conservation and bound correctness."""
        agg = ZoneDemandAggregator()
        rng = random.Random(456)

        for _ in range(100):
            N = rng.randint(8, 50)
            pattern_stops = [(s, f"S_{s}", agg.get_zone_for_stop(s, N), float(s * 1.5)) for s in range(N)]
            
            # Generate random consistent boardings and alightings
            boardings = [float(rng.randint(0, 20)) for _ in range(N)]
            # Construct consistent alightings by running Mode B
            engine = ModeBAlightingInferenceEngine()
            reconstructed = engine.reconstruct_trip(
                pattern_stops=pattern_stops,
                boardings_by_seq={s: int(boardings[s]) for s in range(N)},
            )
            loads = reconstructed["loads"]
            alightings = reconstructed["alightings"]

            trip_zones = agg.aggregate_trip_zones(
                trip_id="TRIP_TEST",
                route_id="R101",
                direction_id=0,
                day_type="weekday",
                trip_date="2026-03-15",
                hour=9,
                pattern_stops=pattern_stops,
                loads=loads,
                boardings=boardings,
                alightings=alightings,
            )

            assert len(trip_zones) <= 8
            # Invariant 1: Boardings total across zones == total trip boardings
            zone_b_sum = sum(z["boardings_total"] for z in trip_zones)
            assert zone_b_sum == pytest.approx(sum(boardings), abs=1e-5)

            # Invariant 2: Alightings total across zones == total trip alightings
            # Mode B alightings are probabilistic expectations; each zone rounds independently to int.
            # Maximum possible round-off drift across up to 8 zones is 8 * 0.5 = 4.
            zone_a_sum = sum(z["alightings_total"] for z in trip_zones)
            assert abs(zone_a_sum - sum(alightings)) <= (len(trip_zones) * 0.5 + 1e-5), (
                f"Zone alightings sum {zone_a_sum} drifted beyond theoretical round-off bound from total {sum(alightings)}"
            )

            # Invariant 3: Mean load bounded by min/max of corresponding zone stops
            for z in trip_zones:
                z_id = z["zone_id"]
                stop_indices = [s for s in range(N) if agg.get_zone_for_stop(s, N) == z_id]
                z_loads = [loads[s] for s in stop_indices]
                assert z["max_load"] == int(np.max(z_loads))
                assert min(z_loads) - 0.01 <= z["mean_load"] <= max(z_loads) + 0.01

    def test_aggregate_hourly_zones_multi_trip(self):
        """Verify grouping and aggregation across multiple trips in the same hour."""
        agg = ZoneDemandAggregator()
        records = [
            {
                "route_id": "R1", "direction_id": 0, "zone_id": 0, "day_type": "weekday",
                "hour": 8, "trip_date": "2026-03-15", "mean_load": 20.0, "max_load": 25,
                "boardings_total": 30, "alightings_total": 10, "trip_count": 1
            },
            {
                "route_id": "R1", "direction_id": 0, "zone_id": 0, "day_type": "weekday",
                "hour": 8, "trip_date": "2026-03-15", "mean_load": 40.0, "max_load": 50,
                "boardings_total": 50, "alightings_total": 20, "trip_count": 1
            },
        ]
        df_hourly = agg.aggregate_hourly_zones(records)
        assert len(df_hourly) == 1
        row = df_hourly.iloc[0]
        assert row["mean_load"] == 30.0  # mean of 20 and 40
        assert row["max_load"] == 50    # max of 25 and 50
        assert row["boardings_total"] == 80  # 30 + 50
        assert row["alightings_total"] == 30  # 10 + 20
        assert row["trip_count"] == 2

