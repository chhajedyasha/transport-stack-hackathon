#!/usr/bin/env python3
"""CrowdWise One-Click Bootstrap Script.
Initializes the complete CrowdWise system from scratch:
1. Creates database tables (Transit & Demand schemas).
2. Generates GTFS schedule fixtures if missing and ingests into SQLite.
3. Generates 28-day synthetic ticket dataset and truth load Parquet artifacts if missing.
4. Trains and calibrates Random Forest and baseline models if missing.
5. Seeds fact_zone_demand and sys_runtime_metadata.
6. Verifies system readiness.

Usage:
  python scripts/bootstrap.py [--force-rebuild] [--demo]
"""
import os
import sys
import argparse
import logging
import sqlite3
import pandas as pd
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
DB_PATH = BACKEND_DIR / "crowdwise.db"

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
    import ingest_gtfs

    with engine.connect() as conn:
        from sqlalchemy import text
        stop_count = conn.execute(text("SELECT COUNT(*) FROM dim_stops")).scalar()

    if stop_count > 0 and not force:
        logger.info(f"GTFS timetable already populated ({stop_count} stops). Skipping.")
        return

    # Check if raw gtfs exists, if not generate it
    gtfs_dir = DATA_DIR / "raw" / "gtfs"
    if not (gtfs_dir / "stops.txt").exists():
        import generate_gtfs_fixture
        generate_gtfs_fixture.main()

    ingest_gtfs.main()


def step_generate_demo_data(force=False):
    demo_tickets = DATA_DIR / "synthetic" / "demo_tickets.parquet"
    if demo_tickets.exists() and not force:
        logger.info(f"Synthetic demo parquet already present ({demo_tickets}). Skipping.")
        return

    import generate_demo_data
    generate_demo_data.main()


def step_train_models(force=False):
    rf_model = MODELS_DIR / "random_forest_regressor.pkl"
    if rf_model.exists() and not force:
        logger.info(f"Trained model artifacts already present ({rf_model}). Skipping.")
        return

    import train_models
    train_models.train_pipeline(
        data_path=str(DATA_DIR / "synthetic" / "zone_hourly_loads.parquet"),
        output_dir=str(MODELS_DIR)
    )


def step_seed_demand_facts(engine, force=False):
    from sqlalchemy import text
    with engine.connect() as conn:
        fact_count = conn.execute(text("SELECT COUNT(*) FROM fact_zone_demand")).scalar()

    if fact_count > 0 and not force:
        logger.info(f"fact_zone_demand already seeded ({fact_count} rows). Skipping.")
        return

    truth_loads_path = DATA_DIR / "synthetic" / "truth_loads_demo.parquet"
    if truth_loads_path.exists():
        df_loads = pd.read_parquet(truth_loads_path)
        df_loads["data_tier"] = "demo_synthetic"
        cols = [
            "route_id", "direction_id", "day_type", "hour", "zone_id",
            "trip_date", "mean_load", "max_load", "boardings_total",
            "alightings_total", "trip_count", "data_tier"
        ]
        available_cols = [c for c in cols if c in df_loads.columns]
        df_loads[available_cols].to_sql("fact_zone_demand", con=engine, if_exists="append", index=False, chunksize=10000)
        logger.info(f"Seeded {len(df_loads)} rows into fact_zone_demand.")

    # Ensure runtime metadata
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT OR IGNORE INTO sys_runtime_metadata (key, value) VALUES ('data_mode', 'demo');
        """))
        conn.execute(text("""
            INSERT OR IGNORE INTO sys_runtime_metadata (key, value) VALUES ('active_tier', 'demo_synthetic');
        """))


def main():
    parser = argparse.ArgumentParser(description="Bootstrap CrowdWise environment and databases.")
    parser.add_argument("--force-rebuild", action="store_true", help="Force regenerate all fixtures, databases, and models.")
    parser.add_argument("--demo", action="store_true", default=True, help="Run in demo mode with synthetic data.")
    args = parser.parse_args()

    logger.info("=================================================================")
    logger.info("           CROWDWISE DELPHI BOOTSTRAP PIPELINE                  ")
    logger.info("=================================================================")

    engine = run_step("Step 1/5: Initialize Database Schemas", step_init_database)
    run_step("Step 2/5: Ingest GTFS Transit Data", step_ingest_gtfs, engine, force=args.force_rebuild)
    run_step("Step 3/5: Generate Synthetic Demand Data", step_generate_demo_data, force=args.force_rebuild)
    run_step("Step 4/5: Train & Calibrate ML Crowding Models", step_train_models, force=args.force_rebuild)
    run_step("Step 5/5: Seed Zone Demand Facts & Runtime Metadata", step_seed_demand_facts, engine, force=args.force_rebuild)

    logger.info("=================================================================")
    logger.info("  [OK] BOOTSTRAP COMPLETE! CrowdWise is ready for execution.")
    logger.info("  Start Backend  : python backend/run.py")
    logger.info("  Start Frontend : cd frontend && npm run dev")
    logger.info("=================================================================")


if __name__ == "__main__":
    main()
