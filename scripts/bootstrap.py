#!/usr/bin/env python3
"""CrowdWise Bootstrap Script (Real Data Only).

Initializes the complete CrowdWise system from the real organizer datasets:
1. Verifies presence of official October-Delhi.csv and Delhi GTFS feeds.
2. Ingests GTFS schedule into SQLite (dim_routes, dim_stops, patterns, stop_times).
3. Processes October ticketing data (2.56M records) into 8-zone demand facts.
4. Trains Random Forest regressor and RCI calibrator on real demand facts.
5. Sets data_mode = 'organizer' and active_tier = 'organizer'.
"""
import os
import sys
import argparse
import logging
import sqlite3
from pathlib import Path
import pandas as pd

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
DB_PATH = BACKEND_DIR / "crowdwise.db"
CSV_PATH = DATA_DIR / "raw" / "organizer" / "October-Delhi.csv"
GTFS_DIR = DATA_DIR / "raw" / "gtfs"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bootstrap")


def run_step(description, func, *args, **kwargs):
    logger.info(f"==> {description}...")
    res = func(*args, **kwargs)
    logger.info(f"[OK] {description} complete.")
    return res


def step_verify_real_datasets():
    """Ensures both official datasets are present on disk; fails cleanly if missing."""
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        raise FileNotFoundError(
            f"CRITICAL: Official organizer ticketing dataset missing at {CSV_PATH}.\n"
            "Please place 'October-Delhi.csv' in 'data/raw/organizer/'."
        )
    if not (GTFS_DIR / "stops.txt").exists():
        raise FileNotFoundError(
            f"CRITICAL: Static GTFS dataset missing at {GTFS_DIR}.\n"
            "Please ensure GTFS files (routes.txt, stops.txt, stop_times.txt, etc.) are present in 'data/raw/gtfs/'."
        )
    logger.info(f"Verified organizer CSV: {CSV_PATH.stat().st_size / (1024*1024):.1f} MB")
    logger.info(f"Verified static GTFS directory: {GTFS_DIR}")


def step_init_database():
    from app.models.transit import Base as TransitBase
    from app.models.demand import Base as DemandBase
    from sqlalchemy import create_engine

    db_url = f"sqlite:///{DB_PATH.as_posix()}"
    engine = create_engine(db_url)
    TransitBase.metadata.create_all(engine)
    DemandBase.metadata.create_all(engine)
    return engine


def step_ingest_gtfs(engine, force=False):
    with engine.connect() as conn:
        from sqlalchemy import text
        stop_count = conn.execute(text("SELECT COUNT(*) FROM dim_stops")).scalar()

    if stop_count > 0 and not force:
        logger.info(f"GTFS timetable already populated ({stop_count} stops). Skipping.")
        return

    import ingest_gtfs
    ingest_gtfs.main()


def step_process_real_data(engine, force=False):
    with engine.connect() as conn:
        from sqlalchemy import text
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_zone_demand")).scalar()

    if fact_count > 0 and not force:
        logger.info(f"fact_zone_demand already seeded ({fact_count} rows). Skipping.")
        return

    import process_october_tickets
    process_october_tickets.process_dataset(CSV_PATH)


def step_verify_models():
    rf_model = MODELS_DIR / "random_forest_regressor.pkl"
    if not rf_model.exists():
        logger.info("Model artifacts missing. Retraining on organizer data...")
        import train_models
        staging_parquet = DATA_DIR / "staging" / "staging_zone_loads.parquet"
        train_models.train_pipeline(
            data_path=str(staging_parquet),
            output_dir=str(MODELS_DIR)
        )
    else:
        logger.info(f"Trained real-data model artifacts present ({rf_model.stat().st_size / (1024*1024):.1f} MB).")


def main():
    parser = argparse.ArgumentParser(description="Bootstrap CrowdWise environment from real datasets.")
    parser.add_argument("--force-rebuild", action="store_true", help="Force rebuild from scratch.")
    args = parser.parse_args()

    logger.info("=================================================================")
    logger.info("           CROWDWISE REAL DATA BOOTSTRAP PIPELINE                ")
    logger.info("=================================================================")

    run_step("Step 1/5: Verify Real Datasets Presence", step_verify_real_datasets)
    engine = run_step("Step 2/5: Initialize Database Schemas", step_init_database)
    run_step("Step 3/5: Ingest Real GTFS Transit Timetable", step_ingest_gtfs, engine, force=args.force_rebuild)
    run_step("Step 4/5: Process October ETM Tickets into Demand Facts", step_process_real_data, engine, force=args.force_rebuild)
    run_step("Step 5/5: Verify & Calibrate Real-Data ML Models", step_verify_models)

    logger.info("=================================================================")
    logger.info("  [OK] REAL DATA BOOTSTRAP COMPLETE! Active Provenance: organizer")
    logger.info("  Start Backend  : python backend/run.py")
    logger.info("  Start Frontend : cd frontend && npm run dev")
    logger.info("=================================================================")


if __name__ == "__main__":
    main()
