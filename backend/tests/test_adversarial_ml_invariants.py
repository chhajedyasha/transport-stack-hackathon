"""Adversarial stress tests for Machine Learning Leakage, Mathematical Invariants, and Boundary Conditions.

Milestone M3 Challenger Test Suite.
Validates:
1. Temporal split leakage immunity and ordering invariants.
2. Feature pipeline target leakage immunity and transformation isolation.
3. RCI mathematical bounds [0.0, 100.0], monotonicity, and threshold classification.
4. Evaluation metrics resilience against zero-division, zero-variance, and n=1 edge cases.
5. Regressor fallback invariants and non-negativity under adversarial inputs.
6. Sanity check harness violation trapping under strict enforcement.
"""
import math
import copy
import pytest
import numpy as np
import pandas as pd

from app.ml.split import chronological_split
from app.ml.features import FeaturePipeline, FEATURE_COLUMNS
from app.ml.models import HistoricalMeanRegressor, CrowdRandomForestRegressor
from app.ml.evaluate import RCICalibrator, evaluate_predictions
from app.ml.sanity_checks import run_sanity_checks, SanityCheckError


# ============================================================================
# 1. TEMPORAL DATA LEAKAGE PROBING
# ============================================================================

def test_chronological_split_rejects_insufficient_distinct_dates():
    """Asserts that chronological_split rejects datasets with < 3 distinct dates."""
    # Case 1: Empty DataFrame
    df_empty = pd.DataFrame({"trip_date": [], "mean_load": []})
    with pytest.raises(ValueError, match="Insufficient distinct dates"):
        chronological_split(df_empty)

    # Case 2: Only 1 distinct date
    df_single_date = pd.DataFrame({
        "trip_date": ["2026-10-01", "2026-10-01", "2026-10-01"],
        "mean_load": [10.0, 20.0, 30.0],
    })
    with pytest.raises(ValueError, match="Insufficient distinct dates"):
        chronological_split(df_single_date)

    # Case 3: Only 2 distinct dates
    df_two_dates = pd.DataFrame({
        "trip_date": ["2026-10-01", "2026-10-02"],
        "mean_load": [15.0, 25.0],
    })
    with pytest.raises(ValueError, match="Insufficient distinct dates"):
        chronological_split(df_two_dates)

    # Case 4: Dates with only NaT / NaNs
    df_all_nulls = pd.DataFrame({
        "trip_date": [None, pd.NaT, np.nan],
        "mean_load": [5.0, 10.0, 15.0],
    })
    with pytest.raises(ValueError, match="Insufficient distinct dates"):
        chronological_split(df_all_nulls)


def test_chronological_split_strict_ordering_and_zero_temporal_leakage():
    """Adversarially feeds shuffled/reversed dates and asserts strict temporal disjointness.
    Invariant: max(train_date) < min(val_date) < min(test_date)
    """
    # Create 20 dates in reversed/scrambled order with duplicate timestamps
    dates = pd.date_range("2026-09-01", periods=20, freq="D").strftime("%Y-%m-%d").tolist()
    shuffled_dates = list(reversed(dates))  # Future dates first

    records = []
    for dt in shuffled_dates:
        for z in range(4):
            records.append({
                "trip_date": dt,
                "route_id": "8UP",
                "direction_id": 0,
                "zone_id": z,
                "day_type": "WEEKDAY",
                "hour": 8,
                "mean_load": float(z * 10),
            })
    df_shuffled = pd.DataFrame(records)

    train_df, val_df, test_df = chronological_split(df_shuffled, train_ratio=0.7, val_ratio=0.15)

    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0

    train_dates = set(train_df["trip_date"].unique())
    val_dates = set(val_df["trip_date"].unique())
    test_dates = set(test_df["trip_date"].unique())

    # 1. Mutual exclusivity of partitions
    assert train_dates.isdisjoint(val_dates), "Train and Val dates must be strictly disjoint"
    assert val_dates.isdisjoint(test_dates), "Val and Test dates must be strictly disjoint"
    assert train_dates.isdisjoint(test_dates), "Train and Test dates must be strictly disjoint"

    # 2. Strict chronological inequality (zero future-to-past leakage)
    max_train = train_df["trip_date"].max()
    min_val = val_df["trip_date"].min()
    max_val = val_df["trip_date"].max()
    min_test = test_df["trip_date"].min()

    assert max_train < min_val, f"Temporal leakage: max_train ({max_train}) >= min_val ({min_val})"
    assert max_val < min_test, f"Temporal leakage: max_val ({max_val}) >= min_test ({min_test})"


def test_chronological_split_partition_coverage_and_boundary_fractions():
    """Verifies partition coverage across boundary ratios."""
    dates = pd.date_range("2026-10-01", periods=5, freq="D").strftime("%Y-%m-%d").tolist()
    df = pd.DataFrame([{"trip_date": d, "mean_load": 10.0} for d in dates])

    # Extreme high train ratio that would leave 0 test dates without safety clamping
    train_df, val_df, test_df = chronological_split(df, train_ratio=0.95, val_ratio=0.05)
    assert len(train_df) >= 1
    assert len(val_df) >= 1
    assert len(test_df) >= 1
    assert train_df["trip_date"].max() < val_df["trip_date"].min() < test_df["trip_date"].min()


# ============================================================================
# 2. TARGET LEAKAGE & PIPELINE ISOLATION PROBING
# ============================================================================

def test_feature_pipeline_fit_immutability():
    """Verifies that FeaturePipeline.fit historical statistics do NOT change when
    validation or test records are appended, transformed, or modified.
    """
    train_df = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8, "mean_load": 40.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 2, "day_type": "WEEKDAY", "hour": 8, "mean_load": 30.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "SUNDAY", "hour": 8, "mean_load": 15.0},
    ])

    pipeline = FeaturePipeline().fit(train_df)

    # Snapshot fitted parameters
    snap_rzh = copy.deepcopy(pipeline.route_zone_hour_stats)
    snap_rz = copy.deepcopy(pipeline.route_zone_stats)
    snap_nh = copy.deepcopy(pipeline.network_hour_stats)
    snap_global = pipeline.global_mean

    # Create adversarial validation dataframe with extreme target values and future data
    val_df = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8, "mean_load": 999999.0},
        {"route_id": "NEW_ROUTE", "direction_id": 1, "zone_id": 7, "day_type": "HOLIDAY", "hour": 23, "mean_load": -500.0},
    ])

    # Transform validation data
    _ = pipeline.transform(val_df)

    # Transform single row fast-path
    _ = pipeline.transform_single("NEW_ROUTE", 1, 7, "HOLIDAY", 23)

    # Assert internal statistics are 100% bit-for-bit unchanged
    assert pipeline.route_zone_hour_stats == snap_rzh
    assert pipeline.route_zone_stats == snap_rz
    assert pipeline.network_hour_stats == snap_nh
    assert pipeline.global_mean == snap_global


def test_feature_pipeline_target_leakage_immunity():
    """Adversarially probes FeaturePipeline.transform to verify that target columns
    are never included in output features, and target values never influence predictors.
    """
    train_df = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8, "mean_load": 25.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 2, "day_type": "WEEKDAY", "hour": 8, "mean_load": 35.0},
    ])
    pipeline = FeaturePipeline().fit(train_df)

    # Input dataframe containing candidate target columns
    eval_df_with_targets = pd.DataFrame([
        {
            "route_id": "8UP",
            "direction_id": 0,
            "zone_id": 1,
            "day_type": "WEEKDAY",
            "hour": 8,
            "mean_load": 10.0,
            "passenger_load": 50.0,
            "pax_count": 100,
            "actual_crowd": 999.0,
            "target": 42.0,
        }
    ])

    X_feat1 = pipeline.transform(eval_df_with_targets)

    # 1. Target columns must NOT be present in output feature matrix
    forbidden_targets = ["mean_load", "passenger_load", "pax_count", "actual_crowd", "target"]
    for col in forbidden_targets:
        assert col not in X_feat1.columns, f"Target leakage: '{col}' found in feature matrix!"

    # 2. Output features must match FEATURE_COLUMNS contract exactly
    assert list(X_feat1.columns) == FEATURE_COLUMNS

    # 3. Alter target values radically and verify feature representation is invariant
    eval_df_tampered = eval_df_with_targets.copy()
    eval_df_tampered["mean_load"] = 888888.88
    eval_df_tampered["passenger_load"] = -9999.0
    eval_df_tampered["pax_count"] = 777777

    X_feat2 = pipeline.transform(eval_df_tampered)
    np.testing.assert_allclose(
        X_feat1.values,
        X_feat2.values,
        err_msg="Transformed features changed when target values were perturbed! Target leakage detected.",
    )

    # 4. Completely remove target column from input dataframe; transform must still succeed
    eval_df_no_target = eval_df_with_targets.drop(columns=["mean_load", "passenger_load", "pax_count", "actual_crowd", "target"])
    X_feat3 = pipeline.transform(eval_df_no_target)
    np.testing.assert_allclose(X_feat1.values, X_feat3.values)


# ============================================================================
# 3. RCI & CATEGORY BOUNDARY MATHEMATICAL STRESS
# ============================================================================

def test_rci_mathematical_bounds_and_monotonicity():
    """Probes RCI computation across negative, zero, fractional, peak, and extreme loads.
    Inputs: load in [-10.0, 0.0, 24.0, 39.9, 40.0, 45.0, 59.9, 60.0, 74.9, 75.0, 90.0, 150.0]
    Invariants:
    1. RCI strictly in [0.0, 100.0]
    2. RCI monotone non-decreasing: load_a <= load_b ==> RCI(load_a) <= RCI(load_b)
    """
    probe_loads = np.array([-10.0, 0.0, 24.0, 39.9, 40.0, 45.0, 59.9, 60.0, 74.9, 75.0, 90.0, 150.0])

    # Test Capacity Mode (Default: rated_capacity = 60.0)
    calibrator = RCICalibrator(rated_capacity=60.0, mode="capacity")
    rcis = calibrator.compute_rci(probe_loads)

    # Invariant 1: Range strictly in [0.0, 100.0]
    assert np.all(rcis >= 0.0), f"RCI below 0.0 detected: {rcis[rcis < 0.0]}"
    assert np.all(rcis <= 100.0), f"RCI above 100.0 detected: {rcis[rcis > 100.0]}"

    # Invariant 2: Monotone non-decreasing
    diffs = np.diff(rcis)
    assert np.all(diffs >= -1e-6), f"Monotonicity violation in RCI mapping: {diffs[diffs < 0]}"

    # Specific analytical check values for capacity=60.0
    assert rcis[0] == 0.0     # -10 clamped to 0
    assert rcis[1] == 0.0     # 0.0 -> 0.0
    assert rcis[2] == 40.0    # 24 / 60 = 0.40 -> 40.0
    assert rcis[3] == 66.5    # 39.9 / 60 = 0.665 -> 66.5
    assert rcis[4] == 66.67   # 40.0 / 60 = 0.6667 -> 66.67
    assert rcis[5] == 75.0    # 45.0 / 60 = 0.75 -> 75.0
    assert rcis[6] == 99.83   # 59.9 / 60 = 0.9983 -> 99.83
    assert rcis[7] == 100.0   # 60.0 / 60 = 1.0 -> 100.0
    assert rcis[8] == 100.0   # 74.9 clamped to 100.0
    assert rcis[9] == 100.0   # 75.0 clamped to 100.0
    assert rcis[10] == 100.0  # 90.0 clamped to 100.0
    assert rcis[11] == 100.0  # 150.0 clamped to 100.0


def test_rci_percentile_mode_monotonicity_and_bounds():
    """Verifies that percentile-calibrated RCI is also strictly bounded and monotone."""
    calibrator = RCICalibrator(mode="percentile")
    y_train = np.linspace(0.0, 70.0, 200)
    calibrator.fit(y_train)

    probe_loads = np.array([-10.0, 0.0, 5.0, 15.0, 35.0, 50.0, 70.0, 120.0])
    rcis = calibrator.compute_rci(probe_loads)

    assert np.all(rcis >= 0.0)
    assert np.all(rcis <= 100.0)
    diffs = np.diff(rcis)
    assert np.all(diffs >= 0.0), "Percentile RCI must be monotonically non-decreasing"


def test_rci_extreme_and_non_finite_inputs():
    """Verifies that NaN, positive inf, and negative inf do not crash or produce invalid RCI."""
    calibrator = RCICalibrator(rated_capacity=60.0, mode="capacity")
    extreme_inputs = np.array([np.nan, np.inf, -np.inf, 1e9, -1e9])

    rcis = calibrator.compute_rci(extreme_inputs)
    assert not np.any(np.isnan(rcis)), "RCI output must not contain NaN"
    assert not np.any(np.isinf(rcis)), "RCI output must not contain inf"
    assert np.all(rcis >= 0.0)
    assert np.all(rcis <= 100.0)


def test_rci_category_and_label_strict_thresholds():
    """Asserts exact category partition boundaries:
    RCI < 40.0: 'Low' / 'Seats Available'
    40.0 <= RCI < 75.0: 'Moderate' / 'Standing Room'
    RCI >= 75.0: 'High' / 'Crowded'
    """
    calibrator = RCICalibrator()

    # Boundary probe points
    test_rcis = np.array([-10.0, 0.0, 24.0, 39.9, 40.0, 45.0, 59.9, 60.0, 74.9, 75.0, 90.0, 150.0])

    expected_categories = [
        "Low",       # -10.0 < 40
        "Low",       # 0.0 < 40
        "Low",       # 24.0 < 40
        "Low",       # 39.9 < 40
        "Moderate",  # 40.0 [40, 75)
        "Moderate",  # 45.0 [40, 75)
        "Moderate",  # 59.9 [40, 75)
        "Moderate",  # 60.0 [40, 75)
        "Moderate",  # 74.9 [40, 75)
        "High",      # 75.0 >= 75
        "High",      # 90.0 >= 75
        "High",      # 150.0 >= 75
    ]

    expected_labels = [
        "Seats Available",
        "Seats Available",
        "Seats Available",
        "Seats Available",
        "Standing Room",
        "Standing Room",
        "Standing Room",
        "Standing Room",
        "Standing Room",
        "Crowded",
        "Crowded",
        "Crowded",
    ]

    actual_categories = calibrator.to_category(test_rcis, style="standard")
    actual_labels = calibrator.to_label(test_rcis)

    assert actual_categories == expected_categories
    assert actual_labels == expected_labels


# ============================================================================
# 4. EVALUATION METRICS ADVERSARIAL EDGE CASES
# ============================================================================

def test_evaluation_metrics_adversarial_zero_division():
    """Tests WAPE on y_true = [0, 0, 0]. Must return 0.0 without ZeroDivisionError."""
    calibrator = RCICalibrator()

    y_true_zero = np.array([0.0, 0.0, 0.0])
    y_pred_zero = np.array([0.0, 0.0, 0.0])
    metrics_zero = evaluate_predictions(y_true_zero, y_pred_zero, calibrator)

    assert metrics_zero["wape"] == 0.0
    assert metrics_zero["wape_percent"] == 0.0
    assert metrics_zero["mae"] == 0.0
    assert metrics_zero["rmse"] == 0.0

    # With non-zero predictions on all-zero ground truth
    y_pred_nonzero = np.array([5.0, 10.0, 15.0])
    metrics_nonzero_pred = evaluate_predictions(y_true_zero, y_pred_nonzero, calibrator)

    assert metrics_nonzero_pred["wape"] == 0.0
    assert metrics_nonzero_pred["wape_percent"] == 0.0
    assert metrics_nonzero_pred["mae"] == 10.0
    assert not math.isnan(metrics_nonzero_pred["wape"])


def test_evaluation_metrics_adversarial_constant_predictions_spearman():
    """Tests Spearman rank correlation on constant predictions y_pred = [25, 25, 25]
    or constant ground truth. Must return 0.0 without NaN or RuntimeWarning.
    """
    calibrator = RCICalibrator()

    # Case 1: Constant y_pred
    y_true = np.array([10.0, 20.0, 30.0])
    y_pred_const = np.array([25.0, 25.0, 25.0])
    metrics1 = evaluate_predictions(y_true, y_pred_const, calibrator)

    assert metrics1["spearman_rank_correlation"] == 0.0
    assert not math.isnan(metrics1["spearman_rank_correlation"])

    # Case 2: Constant y_true
    y_true_const = np.array([15.0, 15.0, 15.0])
    y_pred = np.array([10.0, 20.0, 30.0])
    metrics2 = evaluate_predictions(y_true_const, y_pred, calibrator)

    assert metrics2["spearman_rank_correlation"] == 0.0
    assert not math.isnan(metrics2["spearman_rank_correlation"])

    # Case 3: Both constant
    metrics3 = evaluate_predictions(y_true_const, y_pred_const, calibrator)
    assert metrics3["spearman_rank_correlation"] == 0.0


def test_evaluation_metrics_adversarial_single_sample_n1():
    """Tests evaluation metrics with n = 1 single sample."""
    calibrator = RCICalibrator()
    y_true_single = np.array([30.0])
    y_pred_single = np.array([35.0])

    metrics = evaluate_predictions(y_true_single, y_pred_single, calibrator)

    assert metrics["n_samples"] == 1
    assert metrics["mae"] == 5.0
    assert metrics["rmse"] == 5.0
    assert metrics["wape"] == round(5.0 / 30.0, 4)
    assert metrics["spearman_rank_correlation"] == 0.0
    assert metrics["category_accuracy"] in [0.0, 1.0]
    assert 0.0 <= metrics["category_macro_f1"] <= 1.0


# ============================================================================
# 5. REGRESSOR ROBUSTNESS & NON-NEGATIVITY INVARIANTS
# ============================================================================

def test_historical_mean_regressor_non_negativity_and_complete_fallback():
    """Verifies that HistoricalMeanRegressor handles completely unseen inputs
    and returns non-negative predictions at all 6 hierarchy tiers.
    """
    df_train = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8, "mean_load": 30.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 2, "day_type": "WEEKDAY", "hour": 8, "mean_load": 20.0},
    ])
    model = HistoricalMeanRegressor().fit(df_train)

    # Unseen zone on known route/direction/day_type/hour (Level 2/3 fallback)
    pred_zone = model.predict_single("8UP", 0, 99, "WEEKDAY", 8)
    assert pred_zone >= 0.0

    # Unseen route on known day_type/hour (Level 4 fallback)
    pred_route = model.predict_single("GHOST_ROUTE", 0, 1, "WEEKDAY", 8)
    assert pred_route >= 0.0

    # Unseen day_type and hour (Level 6 global mean fallback)
    pred_global = model.predict_single("GHOST_ROUTE", 99, 99, "SPECIAL_FESTIVAL", 25)
    assert pred_global >= 0.0

    # Batch query containing negative or anomalous identifiers
    df_query = pd.DataFrame([
        {"route_id": "-1", "direction_id": -99, "zone_id": -5, "day_type": "UNKNOWN", "hour": 99},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8},
    ])
    preds = model.predict(df_query)
    assert np.all(preds >= 0.0)


def test_random_forest_confidence_intervals_invariant():
    """Verifies that CrowdRandomForestRegressor produces:
    1. p10 <= mean_pred <= p90
    2. p10 >= 0.0
    3. confidence in ('high', 'medium', 'low')
    """
    np.random.seed(42)
    X_train = np.random.uniform(0.0, 1.0, size=(100, 16))
    y_train = np.random.uniform(5.0, 50.0, size=(100,))

    rf = CrowdRandomForestRegressor(n_estimators=20, max_depth=4, random_state=42)
    rf.fit(X_train, y_train)

    X_test = np.random.uniform(0.0, 1.0, size=(30, 16))
    mean_preds, p10, p90, confs = rf.predict_with_confidence(X_test)

    # Invariants
    assert np.all(p10 >= 0.0), "p10 lower bound must be non-negative"
    assert np.all(p10 <= p90 + 1e-6), "p10 must be <= p90"
    assert np.all(mean_preds >= 0.0), "mean predictions must be non-negative"
    assert len(confs) == len(mean_preds)
    for c in confs:
        assert c in ["high", "medium", "low"]


# ============================================================================
# 6. SANITY CHECK HARNESS ADVERSARIAL TRAPPING
# ============================================================================

def test_sanity_check_traps_negative_load_or_out_of_bounds_rci():
    """Verifies that run_sanity_checks fails and raises SanityCheckError in strict mode
    when load < 0 or RCI not in [0, 100].
    """
    # Negative load
    df_neg_load = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": -5.0, "pred_rci": 10.0},
    ])
    with pytest.raises(SanityCheckError, match="Sanity check validation failed"):
        run_sanity_checks(df_neg_load, strict=True)

    # RCI > 100.0
    df_excess_rci = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 70.0, "pred_rci": 115.0},
    ])
    with pytest.raises(SanityCheckError, match="Sanity check validation failed"):
        run_sanity_checks(df_excess_rci, strict=True)


def test_sanity_check_traps_inverted_peak_or_sunday_higher_than_weekday():
    """Verifies that run_sanity_checks fails when diurnal peak curves are inverted
    or Sunday peak exceeds Weekday peak.
    """
    # Inverted: Midday is 50.0, AM Peak is only 20.0 (AM ratio = 0.40x < 1.25x)
    df_inverted = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 20.0, "pred_rci": 33.3},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 13, "pred_load": 50.0, "pred_rci": 83.3},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 23, "pred_load": 5.0, "pred_rci": 8.3},
    ])
    with pytest.raises(SanityCheckError, match="SC02_PEAK_CURVE"):
        run_sanity_checks(df_inverted, strict=True)

    # Inverted: Sunday peak (60.0) > Weekday peak (30.0)
    df_sunday_higher = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 30.0, "pred_rci": 50.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 18, "pred_load": 30.0, "pred_rci": 50.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 13, "pred_load": 20.0, "pred_rci": 33.3},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 23, "pred_load": 5.0, "pred_rci": 8.3},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "SUNDAY", "hour": 8, "pred_load": 60.0, "pred_rci": 100.0},
    ])
    with pytest.raises(SanityCheckError, match="SC03_WEEKDAY_SUNDAY"):
        run_sanity_checks(df_sunday_higher, strict=True)
