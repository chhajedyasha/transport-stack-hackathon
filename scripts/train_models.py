"""Train baseline and Random Forest models on chronological split data."""
import os
import sys
import json
import logging
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

# Ensure backend is in python path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.ml.split import chronological_split
from app.ml.features import FeaturePipeline
from app.ml.models import HistoricalMeanRegressor, CrowdRandomForestRegressor
from app.ml.evaluate import RCICalibrator, evaluate_predictions
from app.ml.sanity_checks import run_sanity_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def train_pipeline(
    data_path: str = "data/synthetic/zone_hourly_loads.parquet",
    output_dir: str = "models",
) -> dict:
    """End-to-end model training, validation, and serialization."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Loading modeling dataset from {data_path}...")
    df = pd.read_parquet(data_path)
    logger.info(f"Total dataset records: {len(df):,}")
    
    # 1. Chronological Split (70 / 15 / 15)
    df_train, df_val, df_test = chronological_split(df, date_col="trip_date")
    logger.info(
        f"Split sizes: Train={len(df_train):,} ({df_train['trip_date'].min()} to {df_train['trip_date'].max()}) | "
        f"Val={len(df_val):,} ({df_val['trip_date'].min()} to {df_val['trip_date'].max()}) | "
        f"Test={len(df_test):,} ({df_test['trip_date'].min()} to {df_test['trip_date'].max()})"
    )
    
    # 2. Fit Feature Pipeline on Train ONLY
    logger.info("Fitting leakage-safe feature pipeline on training partition...")
    pipeline = FeaturePipeline()
    pipeline.fit(df_train)
    
    X_train = pipeline.transform(df_train).values
    y_train = df_train["mean_load"].values.astype(float)
    
    X_val = pipeline.transform(df_val).values
    y_val = df_val["mean_load"].values.astype(float)
    
    X_test = pipeline.transform(df_test).values
    y_test = df_test["mean_load"].values.astype(float)
    
    # 3. Fit RCI Calibrator on Train distribution
    calibrator = RCICalibrator(rated_capacity=60.0, mode="capacity")
    calibrator.fit(y_train)
    
    # 4. Train Baselines
    logger.info("Training Historical Mean Baseline (B1/B2)...")
    baseline = HistoricalMeanRegressor()
    baseline.fit(df_train)
    baseline_val_preds = baseline.predict(df_val)
    baseline_metrics = evaluate_predictions(y_val, baseline_val_preds, calibrator)
    logger.info(f"Baseline Validation WAPE: {baseline_metrics['wape']:.4f}, MAE: {baseline_metrics['mae']:.2f}")
    
    # 5. Train Random Forest Regressor (45 estimators for optimal GitHub size < 50MB and fast inference)
    logger.info("Training Production RandomForestRegressor...")
    rf = CrowdRandomForestRegressor(n_estimators=45, max_depth=15, random_state=42)
    rf.fit(X_train, y_train)
    
    rf_val_preds = rf.predict(X_val)
    rf_val_metrics = evaluate_predictions(y_val, rf_val_preds, calibrator)
    logger.info(f"RandomForest Validation WAPE: {rf_val_metrics['wape']:.4f}, MAE: {rf_val_metrics['mae']:.2f}")
    
    # Evaluate on holdout test set
    rf_test_preds = rf.predict(X_test)
    test_metrics = evaluate_predictions(y_test, rf_test_preds, calibrator)
    logger.info(
        f"Final Test Evaluation: WAPE={test_metrics['wape']:.4f}, "
        f"MAE={test_metrics['mae']:.2f}, "
        f"Spearman={test_metrics['spearman_rank_correlation']:.4f}, "
        f"Category F1={test_metrics['category_macro_f1']:.4f}"
    )
    
    # 6. Sanity Checks
    df_eval = df_test.copy()
    df_eval["pred_load"] = rf_test_preds
    df_eval["pred_rci"] = calibrator.compute_rci(rf_test_preds)
    sanity_results = run_sanity_checks(df_eval, strict=False)
    logger.info(f"Sanity Checks Overall Result: {sanity_results['overall']}")
    for check in sanity_results["checks"]:
        logger.info(f" - [{check['status']}] {check['name']}: {check['detail']}")
        
    # 7. Save Artifacts
    logger.info(f"Saving artifacts to {out_path}...")
    save_dirs = [out_path]
    # Ensure both models and crowdwise/models are updated if they differ
    alt_dir = Path("crowdwise/models") if out_path == Path("models") else Path("models")
    if alt_dir.exists() and alt_dir.resolve() != out_path.resolve():
        save_dirs.append(alt_dir)

    for target_dir in save_dirs:
        target_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(rf, target_dir / "random_forest_regressor.pkl", compress=3)
        joblib.dump(baseline, target_dir / "baseline_regressor.pkl", compress=3)
        joblib.dump(pipeline, target_dir / "feature_pipeline.pkl", compress=3)
        
        with open(target_dir / "rci_calibrator.json", "w", encoding="utf-8") as f:
            json.dump(calibrator.to_dict(), f, indent=2)
            
        metadata = {
            "version": "1.0.0",
            "model_type": "RandomForestRegressor",
            "dataset_rows": len(df),
            "train_rows": len(df_train),
            "val_rows": len(df_val),
            "test_rows": len(df_test),
            "val_metrics": rf_val_metrics,
            "test_metrics": test_metrics,
            "baseline_metrics": baseline_metrics,
            "sanity_checks": sanity_results,
        }
        with open(target_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
    logger.info("Model training pipeline completed successfully!")
    return metadata


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train CrowdWise baseline and Random Forest models.")
    parser.add_argument("--data-path", default=None, help="Path to zone hourly loads parquet dataset")
    parser.add_argument("--output-dir", default="models", help="Directory to save model artifacts")
    args, _ = parser.parse_known_args()

    data_path = args.data_path
    if not data_path:
        candidates = [
            Path(__file__).parent.parent / "data" / "synthetic" / "zone_hourly_loads.parquet",
            Path("crowdwise/data/synthetic/zone_hourly_loads.parquet"),
            Path("data/synthetic/zone_hourly_loads.parquet"),
        ]
        for c in candidates:
            if c.exists():
                data_path = str(c)
                break
        if not data_path:
            data_path = "data/synthetic/zone_hourly_loads.parquet"
    else:
        # If relative path doesn't exist from cwd, check relative to crowdwise root
        p = Path(data_path)
        if not p.exists() and not p.is_absolute():
            crowdwise_candidate = Path(__file__).parent.parent / data_path
            if crowdwise_candidate.exists():
                data_path = str(crowdwise_candidate)

    train_pipeline(data_path=data_path, output_dir=args.output_dir)
