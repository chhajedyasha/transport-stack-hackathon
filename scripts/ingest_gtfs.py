"""crowdwise/scripts/ingest_gtfs.py
CLI tool to ingest Delhi Buses static GTFS into the 6 compact derived tables.
Usage:
    python scripts/ingest_gtfs.py --gtfs-dir data/raw/gtfs --db-url sqlite:///backend/crowdwise.db
"""
import os
import sys
import time
import argparse
import logging

# Ensure backend package is in python path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.services.gtfs_service import ingest_gtfs_directory
from app.models.transit import get_engine, create_all_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_gtfs_cli")


def main():
    parser = argparse.ArgumentParser(description="Ingest Delhi Buses static GTFS into compact derived tables.")
    parser.add_argument(
        "--gtfs-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "data", "raw", "gtfs"),
        help="Path to GTFS text files directory (default: crowdwise/data/raw/gtfs)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'crowdwise.db'))}",
        help="Target database URL (default: sqlite:///crowdwise/backend/crowdwise.db)",
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100000,
        help="Chunk size for streaming stop_times.txt (default: 100000)",
    )
    args = parser.parse_args()

    gtfs_dir = os.path.abspath(args.gtfs_dir)
    db_url = args.db_url

    logger.info(f"Target GTFS Directory: {gtfs_dir}")
    logger.info(f"Target Database URL: {db_url}")

    if not os.path.exists(gtfs_dir):
        logger.error(f"GTFS directory does not exist: {gtfs_dir}")
        sys.exit(1)

    t0 = time.time()
    try:
        counts = ingest_gtfs_directory(gtfs_dir, db_url, chunksize=args.chunksize)
        elapsed = time.time() - t0
        logger.info("=" * 60)
        logger.info(f"GTFS STATIC INGESTION COMPLETED IN {elapsed:.2f}s")
        logger.info("TABLE SUMMARY:")
        for tbl, count in counts.items():
            logger.info(f"  - {tbl:<20}: {count:>8} rows")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Ingestion failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
