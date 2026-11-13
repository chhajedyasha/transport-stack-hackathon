"""crowdwise/backend/tests/test_adversarial_ml_serving.py
Adversarial Stress-Testing Suite for ML Serving Latency, Resiliency, 3-Tier Fallback Cascade,
and Strict Domain Sanity Check Enforcement (Milestone M3).
Authored by Challenger M3-2 (Serving Latency, Resiliency & Fallback Cascade Challenger).
"""
import os
import sys
import time
import math
import tempfile
import pathlib
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

import pytest
import numpy as np
import pandas as pd

# Add backend directory and crowdwise root to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
crowdwise_dir = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, crowdwise_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.services.ml_service import MLService, MODELS_DIR
from app.ml.features import FeaturePipeline, FEATURE_COLUMNS
from app.ml.models import HistoricalMeanRegressor, CrowdRandomForestRegressor
from app.ml.evaluate import RCICalibrator
from app.ml.sanity_checks import run_sanity_checks, SanityCheckError


# ===========================================================================
# FIXTURES & HELPER BUILDERS
# ===========================================================================

@pytest.fixture
def clean_ml_service():
    """Provides a fresh, isolated MLService instance pointed at the production models directory."""
    return MLService(models_dir=MODELS_DIR)


@pytest.fixture
def empty_models_dir(tmp_path):
    """Provides an empty temporary directory with zero model artifacts."""
    return tmp_path


@pytest.fixture
def baseline_only_models_dir(tmp_path):
    """Provides a temporary directory containing only the baseline regressor and metadata."""
    import shutil
    base_src = MODELS_DIR / "baseline_regressor.pkl"
    meta_src = MODELS_DIR / "metadata.json"
    if base_src.exists():
        shutil.copy(base_src, tmp_path / "baseline_regressor.pkl")
    if meta_src.exists():
        shutil.copy(meta_src, tmp_path / "metadata.json")
    return tmp_path


@pytest.fixture
def valid_diurnal_eval_df():
    """Generates a valid 24-hour evaluation dataframe respecting transit diurnal patterns."""
    rows = []
    # Weekday 24 hours
    for h in range(24):
        if h in [8, 9, 10]:
            load = 42.0  # AM Peak
        elif h in [17, 18, 19, 20]:
            load = 40.0  # PM Peak
        elif 11 <= h <= 15:
            load = 22.0  # Midday (AM / Mid = 1.91 >= 1.25, PM / Mid = 1.82 >= 1.20)
        elif h >= 22 or h <= 5:
            load = 6.0   # Night (Night < Midday: 6.0 < 22.0)
        else:
            load = 18.0
        rci = min(100.0, max(0.0, (load / 60.0) * 100.0))
        rows.append({
            "route_id": "8UP",
            "direction_id": 0,
            "zone_id": 3,
            "day_type": "WEEKDAY",
            "hour": h,
            "pred_load": load,
            "pred_rci": rci,
        })
    # Sunday peak hours
    for h in [8, 9, 18, 19]:
        load = 19.0  # Sunday Peak < Weekday Peak (19.0 < 42.0)
        rci = min(100.0, max(0.0, (load / 60.0) * 100.0))
        rows.append({
            "route_id": "8UP",
            "direction_id": 0,
            "zone_id": 3,
            "day_type": "SUNDAY",
            "hour": h,
            "pred_load": load,
            "pred_rci": rci,
        })
    return pd.DataFrame(rows)


# ===========================================================================
# 1. 3-TIER FALLBACK CASCADE RESILIENCY & EXCEPTION SHIELDING
# ===========================================================================

class TestFallbackCascadeResilience:
    """Stress-tests the 3-tier fallback hierarchy (RF -> Baseline -> Diurnal Heuristic)."""

    def test_scenario_a_full_production_invariants(self, clean_ml_service):
        """Scenario A: Production models loaded (RF + Baseline + Calibrator).
        Verifies contract completeness, bounds, and confidence tiers across diverse inputs.
        """
        assert clean_ml_service.is_loaded is True
        assert clean_ml_service.rf_model is not None
        assert clean_ml_service.baseline_model is not None

        test_cases = [
            ("8UP", 0, 0, "WEEKDAY", 8),
            ("8UP", 0, 3, "WEEKDAY", 13),
            ("8UP", 1, 7, "WEEKDAY", 18),
            ("8UP", 0, 4, "WEEKDAY", 23),
            ("502UP", 0, 2, "SATURDAY", 10),
            ("TMS", 1, 5, "SUNDAY", 19),
            ("TMS", 0, 1, "HOLIDAY", 9),
        ]

        for r, d, z, dt, h in test_cases:
            pred = clean_ml_service.predict_crowd(r, d, z, dt, h)

            # Contract verification
            assert "load" in pred
            assert "rci" in pred
            assert "category" in pred
            assert "crowding_category" in pred
            assert "label" in pred
            assert "crowding_label" in pred
            assert "confidence" in pred
            assert "tier" in pred
            assert "interval" in pred
            assert "model_version" in pred

            # Physical and mathematical boundaries
            assert pred["load"] >= 0.0, f"Negative load {pred['load']} on {r}:{z}:{h}"
            assert 0.0 <= pred["rci"] <= 100.0, f"RCI out of bounds {pred['rci']}"
            assert pred["category"] in ["Low", "Moderate", "High"]
            assert pred["label"] in ["Seats Available", "Standing Room", "Crowded"]
            assert pred["confidence"] in ["low", "medium", "high"]
            assert pred["tier"] == "estimated"
            assert pred["interval"]["p10"] <= pred["interval"]["p90"]
            assert pred["model_version"] == clean_ml_service.metadata.get("version", "1.0.0")

    def test_scenario_b_rf_missing_fallback_to_baseline(self, baseline_only_models_dir):
        """Scenario B: RF artifact missing. Verifies seamless fallback to HistoricalMeanRegressor."""
        service_b = MLService(models_dir=baseline_only_models_dir)

        assert service_b.is_loaded is True
        assert service_b.rf_model is None
        assert service_b.baseline_model is not None

        pred = service_b.predict_crowd(route_id="8UP", direction_id=0, zone_id=3, day_type="WEEKDAY", hour=18)

        assert pred["model_version"] == "baseline_regressor"
        assert pred["confidence"] == "medium"
        assert pred["tier"] == "estimated"
        assert pred["load"] >= 0.0
        assert 0.0 <= pred["rci"] <= 100.0
        assert pred["category"] in ["Low", "Moderate", "High"]
        assert pred["label"] in ["Seats Available", "Standing Room", "Crowded"]
        assert pred["interval"]["p10"] <= pred["interval"]["p90"]

    def test_scenario_c_all_artifacts_missing_diurnal_heuristic(self, empty_models_dir):
        """Scenario C: All artifacts missing. Verifies fallback to domain-informed diurnal heuristic."""
        service_c = MLService(models_dir=empty_models_dir)

        assert service_c.is_loaded is False
        assert service_c.rf_model is None
        assert service_c.baseline_model is None

        # 1. Weekday Peak Hour (e.g. 8 AM)
        pred_peak = service_c.predict_crowd("8UP", 0, 3, "WEEKDAY", 8)
        assert pred_peak["model_version"] == "fallback_heuristic"
        assert pred_peak["confidence"] == "low"
        assert pred_peak["load"] == 38.0
        assert pred_peak["rci"] == round((38.0 / 60.0) * 100.0, 1)  # 63.3
        assert pred_peak["category"] == "Moderate"
        assert pred_peak["label"] == "Standing Room"

        # 2. Weekday Midday Hour (e.g. 13 PM)
        pred_mid = service_c.predict_crowd("8UP", 0, 3, "WEEKDAY", 13)
        assert pred_mid["load"] == 22.0
        assert pred_mid["rci"] == round((22.0 / 60.0) * 100.0, 1)  # 36.7
        assert pred_mid["category"] == "Low"
        assert pred_mid["label"] == "Seats Available"

        # 3. Night Hour (e.g. 23 PM)
        pred_night = service_c.predict_crowd("8UP", 0, 3, "WEEKDAY", 23)
        assert pred_night["load"] == 8.0
        assert pred_night["rci"] == round((8.0 / 60.0) * 100.0, 1)  # 13.3
        assert pred_night["category"] == "Low"

        # 4. Sunday Peak Hour discount (0.75x)
        pred_sun = service_c.predict_crowd("8UP", 0, 3, "SUNDAY", 8)
        assert pred_sun["load"] == round(38.0 * 0.75, 1)  # 28.5
        assert pred_sun["rci"] == round((28.5 / 60.0) * 100.0, 1)  # 47.5

        # 5. Peak > Midday > Night hierarchy holds strictly in heuristic
        assert pred_peak["load"] > pred_mid["load"] > pred_night["load"]
        assert pred_peak["load"] > pred_sun["load"]

    def test_exception_shielding_rf_crash_falls_to_baseline(self, clean_ml_service):
        """Verifies that an unhandled runtime error inside RF inference is caught and falls to Baseline."""
        # Replace rf_model with a mock raising RuntimeError
        mock_rf = MagicMock()
        mock_rf.predict_with_confidence.side_effect = RuntimeError("Adversarial Tree Memory Fault")
        clean_ml_service.rf_model = mock_rf

        pred = clean_ml_service.predict_crowd("8UP", 0, 3, "WEEKDAY", 18)

        # Did NOT crash, fell back to baseline
        assert pred["model_version"] == "baseline_regressor"
        assert pred["confidence"] == "medium"
        assert pred["load"] >= 0.0

    def test_exception_shielding_rf_and_baseline_crashes_fall_to_heuristic(self, clean_ml_service):
        """Verifies that catastrophic failure in both RF and Baseline models falls to Diurnal Heuristic."""
        mock_rf = MagicMock()
        mock_rf.predict_with_confidence.side_effect = RuntimeError("Adversarial RF Failure")
        clean_ml_service.rf_model = mock_rf

        mock_base = MagicMock()
        mock_base.predict_single.side_effect = ValueError("Adversarial Baseline Matrix NaN")
        clean_ml_service.baseline_model = mock_base

        pred = clean_ml_service.predict_crowd("8UP", 0, 3, "WEEKDAY", 18)

        # Did NOT crash, fell back to heuristic
        assert pred["model_version"] == "fallback_heuristic"
        assert pred["confidence"] == "low"
        assert pred["load"] == 38.0

    def test_exception_shielding_calibrator_crash_gracefully_handled(self, clean_ml_service):
        """Verifies that if RCICalibrator throws an exception, inference does not fail."""
        mock_calib = MagicMock()
        mock_calib.compute_rci.side_effect = ZeroDivisionError("Simulated Calibrator Failure")
        clean_ml_service.calibrator = mock_calib

        # In Tier 1, exception causes fallback to Tier 2 (which uses calibrator and falls to Tier 3)
        pred = clean_ml_service.predict_crowd("8UP", 0, 3, "WEEKDAY", 18)
        assert pred is not None
        assert pred["load"] >= 0.0
        assert 0.0 <= pred["rci"] <= 100.0

    def test_route_matrix_fallback_under_rf_failure(self, clean_ml_service):
        """Verifies that vectorized route matrix falls back to point-wise loop when RF fails."""
        mock_rf = MagicMock()
        mock_rf.predict_with_confidence.side_effect = RuntimeError("Vectorization Batch Crash")
        clean_ml_service.rf_model = mock_rf

        matrix = clean_ml_service.predict_route_matrix("8UP", 0, "WEEKDAY")
        assert len(matrix) == 8
        for zone_row in matrix:
            assert len(zone_row["hours"]) == 24
            for cell in zone_row["hours"]:
                assert cell["load"] >= 0.0
                assert 0.0 <= cell["rci"] <= 100.0
                assert cell["category"] in ["Low", "Moderate", "High"]

    @pytest.mark.parametrize("corrupt_input", [
        {"route_id": "NONEXISTENT_CORRIDOR_XYZ_9999", "direction_id": 0, "zone_id": 3, "day_type": "WEEKDAY", "hour": 18},
        {"route_id": "8UP", "direction_id": 1, "zone_id": 999, "day_type": "WEEKDAY", "hour": 8},
        {"route_id": "8UP", "direction_id": 0, "zone_id": -5, "day_type": "WEEKDAY", "hour": 12},
        {"route_id": "8UP", "direction_id": -99, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "UNOBSERVED_DAY_TYPE", "hour": 8},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": -10},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 999},
        {"route_id": "", "direction_id": 0, "zone_id": 0, "day_type": "", "hour": 0},
    ])
    def test_adversarial_corrupt_inputs_never_crash(self, clean_ml_service, corrupt_input):
        """Stress-tests unobserved, negative, or absurd inputs across the serving layer."""
        pred = clean_ml_service.predict_crowd(**corrupt_input)
        assert pred is not None
        assert pred["load"] >= 0.0
        assert 0.0 <= pred["rci"] <= 100.0
        assert pred["category"] in ["Low", "Moderate", "High"]
        assert pred["tier"] == "estimated"


# ===========================================================================
# 2. SERVING LATENCY & THROUGHPUT SLA BENCHMARKS
# ===========================================================================

class TestServingLatencyAndThroughputSLA:
    """Rigorous empirical validation of serving latency constraints and SLAs."""

    def test_transform_single_latency_sla(self, clean_ml_service):
        """SLA: Execution latency of transform_single() must be < 0.05 ms (50 us) per call.
        Benchmark executed over 1,000 continuous invocations.
        """
        pipeline = clean_ml_service.feature_pipeline
        assert pipeline is not None, "FeaturePipeline must be loaded for latency benchmark"

        # Warm-up (100 calls)
        for _ in range(100):
            pipeline.transform_single("8UP", 0, 3, "WEEKDAY", 8)

        # Timed benchmark: 1,000 invocations
        num_calls = 1000
        t0 = time.perf_counter()
        for _ in range(num_calls):
            pipeline.transform_single("8UP", 0, 3, "WEEKDAY", 8)
        elapsed_total_s = time.perf_counter() - t0

        mean_latency_ms = (elapsed_total_s * 1000.0) / num_calls

        print(f"\n[LATENCY BENCHMARK] transform_single(): {mean_latency_ms:.5f} ms/call ({elapsed_total_s*1000:.2f} ms for {num_calls} calls)")

        # SLA Assertions
        assert mean_latency_ms < 0.05, f"transform_single SLA breached: {mean_latency_ms:.5f} ms >= 0.05 ms SLA"
        assert elapsed_total_s * 1000.0 < 50.0, f"Total 1,000-call time breached: {elapsed_total_s*1000:.2f} ms >= 50.0 ms"

    def test_predict_route_matrix_latency_sla(self, clean_ml_service):
        """SLA: Execution latency of predict_route_matrix() across 192 cells (8 zones x 24 hours)
        must complete in < 300 ms.
        """
        # Warm-up run
        clean_ml_service.predict_route_matrix("8UP", 0, "WEEKDAY")

        # Measure 10 runs to verify stability
        runs = 10
        latencies_ms = []
        for _ in range(runs):
            t0 = time.perf_counter()
            matrix = clean_ml_service.predict_route_matrix("8UP", 0, "WEEKDAY")
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        mean_latency = np.mean(latencies_ms)
        max_latency = np.max(latencies_ms)
        min_latency = np.min(latencies_ms)

        print(f"\n[LATENCY BENCHMARK] predict_route_matrix() (192 cells): Mean={mean_latency:.2f} ms, Min={min_latency:.2f} ms, Max={max_latency:.2f} ms")

        # Verify output structure: 8 zones x 24 hours = 192 cells
        assert len(matrix) == 8
        total_cells = sum(len(z["hours"]) for z in matrix)
        assert total_cells == 192

        # SLA Assertions
        assert max_latency < 300.0, f"predict_route_matrix SLA breached: Max latency {max_latency:.2f} ms >= 300 ms SLA"
        assert mean_latency < 150.0, f"predict_route_matrix average too slow: {mean_latency:.2f} ms"

    def test_single_point_predict_crowd_throughput(self, clean_ml_service):
        """Measures single-point predict_crowd() throughput across 100 invocations (< 25.0 ms/call)."""
        # Warm-up
        for _ in range(10):
            clean_ml_service.predict_crowd("8UP", 0, 3, "WEEKDAY", 8)

        num_calls = 100
        t0 = time.perf_counter()
        for i in range(num_calls):
            clean_ml_service.predict_crowd("8UP", 0, i % 8, "WEEKDAY", (i % 24))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        mean_ms = elapsed_ms / num_calls

        print(f"\n[LATENCY BENCHMARK] predict_crowd() single-point: {mean_ms:.3f} ms/call ({elapsed_ms:.1f} ms for {num_calls} calls)")
        assert mean_ms < 25.0, f"predict_crowd SLA breached: {mean_ms:.3f} ms >= 25.0 ms"

    def test_predict_journey_zones_multi_leg_latency(self, clean_ml_service):
        """Measures multi-leg journey zone evaluation latency (e.g. 5-zone traversal, < 100 ms)."""
        zone_ids = [1, 2, 3, 4, 5]
        t0 = time.perf_counter()
        for _ in range(10):
            res = clean_ml_service.predict_journey_zones("8UP", 0, zone_ids, "WEEKDAY", 18)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0 / 10.0

        assert len(res) == 5
        print(f"\n[LATENCY BENCHMARK] predict_journey_zones(5 zones): {elapsed_ms:.3f} ms/journey")
        assert elapsed_ms < 100.0, f"predict_journey_zones SLA breached: {elapsed_ms:.3f} ms >= 100.0 ms"

    def test_fallback_cascade_latency_under_sla(self, clean_ml_service):
        """Asserts that Tier 2 (Baseline) and Tier 3 (Heuristic) fallbacks remain well within SLA."""
        # Tier 2 Baseline only
        clean_ml_service.rf_model = None
        t0 = time.perf_counter()
        m_base = clean_ml_service.predict_route_matrix("8UP", 0, "WEEKDAY")
        el_base = (time.perf_counter() - t0) * 1000.0
        assert len(m_base) == 8
        assert el_base < 100.0, f"Baseline route matrix too slow: {el_base:.2f} ms"

        # Tier 3 Heuristic only
        clean_ml_service.baseline_model = None
        t0 = time.perf_counter()
        m_heur = clean_ml_service.predict_route_matrix("8UP", 0, "WEEKDAY")
        el_heur = (time.perf_counter() - t0) * 1000.0
        assert len(m_heur) == 8
        assert el_heur < 50.0, f"Heuristic route matrix too slow: {el_heur:.2f} ms"


# ===========================================================================
# 3. STRICT SANITY CHECK HARNESS ENFORCEMENT & ADVERSARIAL REJECTIONS
# ===========================================================================

class TestStrictSanityCheckEnforcement:
    """Stress-tests automated transit domain invariant validation and strict rejection."""

    def test_sanity_checks_pass_on_valid_profile(self, valid_diurnal_eval_df):
        """Verifies that a genuine transit diurnal curve passes all sanity checks with strict=True."""
        results = run_sanity_checks(valid_diurnal_eval_df, strict=True)
        assert results["overall"] == "PASS"

        check_map = {c["id"]: c["status"] for c in results["checks"]}
        assert check_map["SC01_BOUNDS"] == "PASS"
        assert check_map["SC02_PEAK_CURVE"] == "PASS"
        assert check_map["SC03_WEEKDAY_SUNDAY"] == "PASS"

    def test_strict_rejection_negative_load(self, valid_diurnal_eval_df):
        """SC01: Negative load in prediction dataframe MUST raise SanityCheckError in strict mode."""
        df_bad = valid_diurnal_eval_df.copy()
        df_bad.loc[0, "pred_load"] = -0.5

        # Strict mode: raises SanityCheckError
        with pytest.raises(SanityCheckError) as exc_info:
            run_sanity_checks(df_bad, strict=True)
        assert "SC01_BOUNDS" in str(exc_info.value)

        # Non-strict mode: reports overall FAIL without throwing
        res_soft = run_sanity_checks(df_bad, strict=False)
        assert res_soft["overall"] == "FAIL"

    def test_strict_rejection_out_of_bounds_rci(self, valid_diurnal_eval_df):
        """SC01: RCI > 100.0 or < 0.0 MUST raise SanityCheckError in strict mode."""
        df_bad_high = valid_diurnal_eval_df.copy()
        df_bad_high.loc[0, "pred_rci"] = 101.5

        with pytest.raises(SanityCheckError):
            run_sanity_checks(df_bad_high, strict=True)

        df_bad_low = valid_diurnal_eval_df.copy()
        df_bad_low.loc[0, "pred_rci"] = -1.0

        with pytest.raises(SanityCheckError):
            run_sanity_checks(df_bad_low, strict=True)

    def test_strict_rejection_inverted_am_peak(self, valid_diurnal_eval_df):
        """SC02: AM Peak < 1.25 * Midday MUST raise SanityCheckError."""
        df_bad = valid_diurnal_eval_df.copy()
        # Invert AM peak: set 8, 9, 10 AM to 15 passengers (Midday is 22 passengers -> ratio 0.68x)
        df_bad.loc[df_bad["hour"].isin([8, 9, 10]), "pred_load"] = 15.0

        with pytest.raises(SanityCheckError) as exc_info:
            run_sanity_checks(df_bad, strict=True)
        assert "SC02_PEAK_CURVE" in str(exc_info.value)

    def test_strict_rejection_inverted_pm_peak(self, valid_diurnal_eval_df):
        """SC02: PM Peak < 1.20 * Midday MUST raise SanityCheckError."""
        df_bad = valid_diurnal_eval_df.copy()
        # Flatten PM peak: set 17..20 to 22.0 passengers (Midday is 22.0 passengers -> ratio 1.0x < 1.19x)
        df_bad.loc[df_bad["hour"].isin([17, 18, 19, 20]), "pred_load"] = 22.0

        with pytest.raises(SanityCheckError) as exc_info:
            run_sanity_checks(df_bad, strict=True)
        assert "SC02_PEAK_CURVE" in str(exc_info.value)

    def test_strict_rejection_inverted_night_curve(self, valid_diurnal_eval_df):
        """SC02: Night load > Midday load MUST raise SanityCheckError."""
        df_bad = valid_diurnal_eval_df.copy()
        # Invert night: set night hours (22..5) to 30.0 passengers (Midday is 22.0 passengers)
        df_bad.loc[df_bad["hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]), "pred_load"] = 30.0

        with pytest.raises(SanityCheckError) as exc_info:
            run_sanity_checks(df_bad, strict=True)
        assert "SC02_PEAK_CURVE" in str(exc_info.value)

    def test_strict_rejection_sunday_higher_than_weekday_peak(self, valid_diurnal_eval_df):
        """SC03: Sunday Peak > Weekday Peak MUST raise SanityCheckError."""
        df_bad = valid_diurnal_eval_df.copy()
        # Weekday peak is ~42.0. Invert Sunday peak to 55.0 passengers
        df_bad.loc[df_bad["day_type"] == "SUNDAY", "pred_load"] = 55.0

        with pytest.raises(SanityCheckError) as exc_info:
            run_sanity_checks(df_bad, strict=True)
        assert "SC03_WEEKDAY_SUNDAY" in str(exc_info.value)

    def test_boundary_precision_am_peak_multiplier(self, valid_diurnal_eval_df):
        """SC02: Tests boundary condition at AM ratio 1.23x (fails) vs 1.25x (passes)."""
        df_eval = valid_diurnal_eval_df.copy()
        mid_load = 20.0
        df_eval.loc[df_eval["hour"].isin([11, 12, 13, 14, 15]), "pred_load"] = mid_load

        # 1. AM load = 24.6 (ratio = 24.6 / 20.0 = 1.23x < 1.24x boundary) -> FAILS
        df_eval.loc[df_eval["hour"].isin([8, 9, 10]), "pred_load"] = 24.6
        with pytest.raises(SanityCheckError):
            run_sanity_checks(df_eval, strict=True)

        # 2. AM load = 25.0 (ratio = 25.0 / 20.0 = 1.25x >= 1.24x boundary) -> PASSES
        df_eval.loc[df_eval["hour"].isin([8, 9, 10]), "pred_load"] = 25.0
        # PM ratio also >= 1.20
        df_eval.loc[df_eval["hour"].isin([17, 18, 19, 20]), "pred_load"] = 26.0
        # Night < Mid
        df_eval.loc[df_eval["hour"].isin([22, 23, 0, 1, 2, 3, 4, 5]), "pred_load"] = 5.0
        # Sunday peak < Weekday peak
        df_eval.loc[df_eval["day_type"] == "SUNDAY", "pred_load"] = 15.0

        res = run_sanity_checks(df_eval, strict=True)
        assert res["overall"] == "PASS"

    def test_empty_dataframe_rejection(self):
        """Verifies that an empty evaluation dataframe fails checks and raises in strict mode."""
        df_empty = pd.DataFrame(columns=["route_id", "direction_id", "zone_id", "day_type", "hour", "pred_load", "pred_rci"])
        with pytest.raises(SanityCheckError):
            run_sanity_checks(df_empty, strict=True)
