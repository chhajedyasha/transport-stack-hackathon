"""Unit tests for ML pipeline, leakage prevention, and crowdedness forecasting."""
import pytest
import numpy as np
import pandas as pd

from app.ml.split import chronological_split
from app.ml.features import FeaturePipeline, FEATURE_COLUMNS
from app.ml.models import HistoricalMeanRegressor, CrowdRandomForestRegressor
from app.ml.evaluate import RCICalibrator, evaluate_predictions
from app.ml.sanity_checks import run_sanity_checks, SanityCheckError
from app.services.ml_service import MLService


@pytest.fixture
def sample_load_df():
    """Generates synthetic hourly load rows across 14 consecutive dates."""
    dates = pd.date_range("2026-10-01", periods=14, freq="D").strftime("%Y-%m-%d").tolist()
    records = []
    for dt in dates:
        day_type = "SUNDAY" if pd.to_datetime(dt).dayofweek == 6 else ("SATURDAY" if pd.to_datetime(dt).dayofweek == 5 else "WEEKDAY")
        for h in [8, 12, 18, 23]:
            for z in [0, 3, 7]:
                base = 35.0 if h in [8, 18] else (5.0 if h == 23 else 20.0)
                records.append({
                    "route_id": "8UP",
                    "direction_id": 0,
                    "zone_id": z,
                    "day_type": day_type,
                    "hour": h,
                    "trip_date": dt,
                    "mean_load": base + float(z),
                    "trip_count": 2,
                })
    return pd.DataFrame(records)


def test_chronological_split_invariant(sample_load_df):
    """Asserts strict chronological split without temporal leakage."""
    train_df, val_df, test_df = chronological_split(sample_load_df, date_col="trip_date")
    
    assert len(train_df) > 0
    assert len(val_df) > 0
    assert len(test_df) > 0
    
    max_train = train_df["trip_date"].max()
    min_val = val_df["trip_date"].min()
    max_val = val_df["trip_date"].max()
    min_test = test_df["trip_date"].min()
    
    assert max_train < min_val, f"Leakage: max_train={max_train} >= min_val={min_val}"
    assert max_val < min_test, f"Leakage: max_val={max_val} >= min_test={min_test}"


def test_chronological_split_minimal_3_days():
    """Verifies minimal 3-date boundary case produces 1 day in each partition."""
    df3 = pd.DataFrame({
        "trip_date": ["2026-10-01", "2026-10-02", "2026-10-03"],
        "mean_load": [10.0, 20.0, 30.0],
    })
    tr, va, te = chronological_split(df3)
    assert len(tr) == 1
    assert len(va) == 1
    assert len(te) == 1
    assert tr["trip_date"].max() < va["trip_date"].min() < te["trip_date"].min()


def test_chronological_split_null_dates_filter():
    """Verifies null or NaT dates are filtered without crashing."""
    df_nulls = pd.DataFrame({
        "trip_date": ["2026-10-01", None, "2026-10-02", "2026-10-03", pd.NaT],
        "mean_load": [10.0, 15.0, 20.0, 30.0, 35.0],
    })
    tr, va, te = chronological_split(df_nulls)
    assert len(tr) == 1 and len(va) == 1 and len(te) == 1


def test_feature_pipeline_no_target_in_features(sample_load_df):
    """Verifies that transformed feature matrix does not leak target columns."""
    train_df, val_df, _ = chronological_split(sample_load_df)
    pipeline = FeaturePipeline().fit(train_df)
    
    X_val = pipeline.transform(val_df)
    assert "mean_load" not in X_val.columns
    assert "passenger_count" not in X_val.columns
    assert list(X_val.columns) == FEATURE_COLUMNS
    assert len(X_val) == len(val_df)


def test_feature_pipeline_fast_path_and_sunday_mapping(sample_load_df):
    """Verifies Sunday maps to day_of_week=6 and transform_single produces identical vector."""
    train_df, _, _ = chronological_split(sample_load_df)
    pipeline = FeaturePipeline().fit(train_df)
    
    vec = pipeline.transform_single("8UP", 0, 3, "SUNDAY", 8)
    assert vec.shape == (1, 16)
    assert vec[0, 6] == 6.0  # Sunday day_of_week
    assert vec[0, 7] == 1.0  # is_weekend
    
    df_single = pd.DataFrame([{
        "route_id": "8UP",
        "direction_id": 0,
        "zone_id": 3,
        "day_type": "SUNDAY",
        "hour": 8,
    }])
    vec_batch = pipeline.transform(df_single).values
    assert np.allclose(vec, vec_batch)


def test_historical_mean_regressor_fallback_levels():
    """Verifies HistoricalMeanRegressor complete 6-level fallback hierarchy, holiday mapping, and clamping."""
    df_train = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8, "mean_load": 40.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 2, "day_type": "WEEKDAY", "hour": 8, "mean_load": 30.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 3, "day_type": "SUNDAY", "hour": 8, "mean_load": 15.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 4, "day_type": "WEEKDAY", "hour": 8, "mean_load": np.nan},
    ])
    model = HistoricalMeanRegressor().fit(df_train)
    
    # Exact match Level 0
    assert model.predict_single("8UP", 0, 1, "WEEKDAY", 8) == 40.0
    
    # Level 1/2 fallback (unseen zone 9 on route 8UP at hour 8)
    pred_zone_fallback = model.predict_single("8UP", 0, 9, "WEEKDAY", 8)
    assert pred_zone_fallback >= 0.0
    
    # Level 5 fallback (completely unseen route 999 at hour 8)
    pred_route_fallback = model.predict_single("999", 0, 1, "WEEKDAY", 8)
    assert pred_route_fallback >= 0.0
    
    # Holiday mapped to Sunday baseline
    pred_holiday = model.predict_single("8UP", 0, 3, "HOLIDAY", 8)
    assert pred_holiday == 15.0
    
    # Batch predict clamp
    df_query = pd.DataFrame([{"route_id": "8UP", "direction_id": 0, "zone_id": 1, "day_type": "WEEKDAY", "hour": 8}])
    preds = model.predict(df_query)
    assert np.all(preds >= 0.0)


def test_rci_calibrator_bounds_and_categories():
    """Tests RCI capacity mode, percentile mode, categories, and labels."""
    calibrator = RCICalibrator(rated_capacity=60.0, mode="capacity")
    y_train = np.array([0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    calibrator.fit(y_train)
    
    test_y = np.array([-5.0, 0.0, 30.0, 36.0, 60.0, 90.0])
    rci = calibrator.compute_rci(test_y)
    
    # Assert bounds [0, 100]
    assert np.all(rci >= 0.0)
    assert np.all(rci <= 100.0)
    assert rci[1] == 0.0    # 0 pax -> 0 RCI
    assert rci[2] == 50.0   # 30 pax -> 50 RCI
    assert rci[3] == 60.0   # 36 pax -> 60 RCI (Moderate)
    assert rci[4] == 100.0  # 60 pax -> 100 RCI (High)
    assert rci[5] == 100.0  # 90 pax -> clamped 100 RCI
    
    # Test categories
    cats = calibrator.to_category(rci)
    assert cats == ["Low", "Low", "Moderate", "Moderate", "High", "High"]
    
    # Test commuter labels
    labels = calibrator.to_label(rci)
    assert labels == ["Seats Available", "Seats Available", "Standing Room", "Standing Room", "Crowded", "Crowded"]


def test_sanity_check_harness_pass():
    """Tests that domain sanity check harness passes on diurnal patterns."""
    df_eval = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 40.0, "pred_rci": 66.7},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 18, "pred_load": 45.0, "pred_rci": 75.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 13, "pred_load": 22.0, "pred_rci": 36.7},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 23, "pred_load": 5.0, "pred_rci": 8.3},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "SUNDAY", "hour": 8, "pred_load": 18.0, "pred_rci": 30.0},
    ])
    results = run_sanity_checks(df_eval, strict=True)
    assert results["overall"] == "PASS"
    check_ids = [c["id"] for c in results["checks"]]
    assert "SC01_BOUNDS" in check_ids
    assert "SC02_PEAK_CURVE" in check_ids
    assert "SC03_WEEKDAY_SUNDAY" in check_ids


def test_sanity_check_strict_failure():
    """Verifies that strict=True raises SanityCheckError on inverted diurnal curves."""
    df_bad = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 10.0, "pred_rci": 16.7},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 13, "pred_load": 30.0, "pred_rci": 50.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 23, "pred_load": 5.0, "pred_rci": 8.3},
    ])
    with pytest.raises(SanityCheckError):
        run_sanity_checks(df_bad, strict=True)


def test_ml_service_prediction_contract():
    """Verifies that MLService produces standard prediction dictionary."""
    service = MLService.get_instance()
    pred = service.predict_crowd(route_id="8UP", direction_id=0, zone_id=3, day_type="WEEKDAY", hour=18)
    
    assert "load" in pred
    assert "rci" in pred
    assert "category" in pred
    assert "label" in pred
    assert "confidence" in pred
    assert "interval" in pred
    assert pred["tier"] == "estimated"
    assert 0.0 <= pred["rci"] <= 100.0
    assert pred["category"] in ["Low", "Moderate", "High"]
    assert pred["label"] in ["Seats Available", "Standing Room", "Crowded"]
    assert pred["confidence"] in ["high", "medium", "low"]
    assert "p10" in pred["interval"] and "p90" in pred["interval"]


def test_ml_service_predict_route_matrix():
    """Verifies high performance route matrix generation."""
    service = MLService.get_instance()
    matrix = service.predict_route_matrix(route_id="8UP", direction_id=0, day_type="WEEKDAY")
    assert len(matrix) == 8
    for row in matrix:
        assert "zone_id" in row
        assert len(row["hours"]) == 24
        assert "load" in row["hours"][0]
        assert "rci" in row["hours"][0]

