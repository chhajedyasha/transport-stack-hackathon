#!/usr/bin/env python3
"""Run automated domain sanity checks against trained models and test datasets."""
import os
import sys
from pathlib import Path
import pandas as pd

# Add backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))

from app.services.ml_service import MLService
from app.ml.sanity_checks import run_sanity_checks


def main():
    print("=" * 65)
    print("        CROWDWISE TRANSIT DOMAIN SANITY CHECK HARNESS        ")
    print("=" * 65)

    data_candidates = [
        root_dir / "data" / "synthetic" / "zone_hourly_loads.parquet",
        root_dir / "data" / "staging" / "staging_zone_loads.parquet",
    ]
    data_path = next((p for p in data_candidates if p.exists()), None)

    if not data_path:
        print("[FAIL] No dataset found to run sanity checks. Run python scripts/bootstrap.py first.")
        sys.exit(1)

    print(f"Loading evaluation dataset: {data_path.name}")
    df = pd.read_parquet(data_path)
    if "data_tier" not in df.columns:
        df["data_tier"] = "demo_synthetic"

    # Sample representative slice for fast verification
    eval_df = df.sample(min(len(df), 500), random_state=42).copy().reset_index(drop=True)

    ml_service = MLService.get_instance()

    print(f"Generating model predictions for {len(eval_df)} representative zone-hour observations...")
    predictions = []
    rcis = []
    for _, row in eval_df.iterrows():
        pred = ml_service.predict_crowd(
            route_id=str(row["route_id"]),
            direction_id=int(row["direction_id"]),
            zone_id=int(row["zone_id"]),
            day_type=str(row["day_type"]),
            hour=int(row["hour"]),
        )
        predictions.append(pred["load"])
        rcis.append(pred["rci"])

    eval_df["pred_load"] = predictions
    eval_df["pred_rci"] = rcis

    report = run_sanity_checks(eval_df, pred_col="pred_load", rci_col="pred_rci")

    print("\n" + "=" * 65)
    print("                  SANITY CHECK SCORECARD                  ")
    print("=" * 65)

    for c in report["checks"]:
        status_tag = "[PASS]" if c["status"] == "PASS" else "[FAIL]"
        print(f"{status_tag} {c['id']}: {c['name']}")
        print(f"       Details: {c['detail']}\n")

    print("=" * 65)
    if report["overall"] == "PASS":
        print("  RESULT: ALL REQUIRED DOMAIN SANITY CHECKS PASSED (100% GREEN) ")
    else:
        print("  RESULT: SOME CHECKS FAILED                                    ")
    print("=" * 65)


if __name__ == "__main__":
    main()
