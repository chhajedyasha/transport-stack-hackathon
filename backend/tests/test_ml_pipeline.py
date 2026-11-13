"""Unit tests for ML pipeline, leakage prevention, and crowdedness forecasting."""
import pytest
import numpy as np
import pandas as pd

from app.ml.split import chronological_split
from app.ml.features import FeaturePipeline, FEATURE_COLUMNS
from app.ml.models import HistoricalMeanRegressor, CrowdRandomForestRegressor
from app.ml.evaluate import RCICalibrator, evaluate_predictions
from app.ml.sanity_checks import run_sanity_checks
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


def test_feature_pipeline_no_target_in_features(sample_load_df):
    """Verifies that transformed feature matrix does not leak target columns."""
    train_df, val_df, _ = chronological_split(sample_load_df)
    pipeline = FeaturePipeline().fit(train_df)
    
    X_val = pipeline.transform(val_df)
    assert "mean_load" not in X_val.columns
    assert "passenger_count" not in X_val.columns
    assert list(X_val.columns) == FEATURE_COLUMNS
    assert len(X_val) == len(val_df)


def test_rci_calibrator_bounds_and_categories():
    """Tests RCI percentile ranking and categorical mapping."""
    calibrator = RCICalibrator()
    y_train = np.array([0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    calibrator.fit(y_train)
    
    test_y = np.array([-5.0, 0.0, 15.0, 35.0, 80.0])
    rci = calibrator.compute_rci(test_y)
    
    # Assert bounds [0, 100]
    assert np.all(rci >= 0.0)
    assert np.all(rci <= 100.0)
    
    # Test categories
    cats = calibrator.to_category(rci)
    assert len(cats) == 5
    assert all(c in ["Seats Available", "Standing Room", "Crowded"] for c in cats)


def test_sanity_check_harness_pass():
    """Tests that domain sanity check harness passes on diurnal patterns."""
    df_eval = pd.DataFrame([
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 8, "pred_load": 40.0, "pred_rci": 85.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 18, "pred_load": 45.0, "pred_rci": 90.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 13, "pred_load": 22.0, "pred_rci": 50.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "WEEKDAY", "hour": 23, "pred_load": 5.0, "pred_rci": 10.0},
        {"route_id": "8UP", "direction_id": 0, "zone_id": 0, "day_type": "SUNDAY", "hour": 8, "pred_load": 18.0, "pred_rci": 40.0},
    ])
    results = run_sanity_checks(df_eval)
    assert results["overall"] == "PASS"
    check_ids = [c["id"] for c in results["checks"]]
    assert "SC01_BOUNDS" in check_ids
    assert "SC02_PEAK_CURVE" in check_ids


def test_ml_service_prediction_contract():
    """Verifies that MLService produces standard prediction dictionary."""
    service = MLService.get_instance()
    pred = service.predict_crowd(route_id="8UP", direction_id=0, zone_id=3, day_type="WEEKDAY", hour=18)
    
    assert "load" in pred
    assert "rci" in pred
    assert "category" in pred
    assert "confidence" in pred
    assert pred["tier"] == "estimated"
    assert pred["rci"] >= 0.0 and pred["rci"] <= 100.0
    assert pred["category"] in ["Seats Available", "Standing Room", "Crowded"]
    assert pred["confidence"] in ["high", "medium", "low"]
