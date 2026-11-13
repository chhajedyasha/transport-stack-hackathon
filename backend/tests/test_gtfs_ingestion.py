"""crowdwise/backend/tests/test_gtfs_ingestion.py
Integration tests for the GTFS ingestion pipeline and query interface (M1).
"""
import os
import sys
import tempfile
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
crowdwise_dir = os.path.abspath(os.path.join(backend_dir, ".."))
scripts_dir = os.path.join(crowdwise_dir, "scripts")
for p in [backend_dir, crowdwise_dir, scripts_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.models.transit import Base
from app.services.gtfs_service import (
    ingest_gtfs_directory,
    get_stop_sequence,
    load_all_stops,
    get_route_patterns,
    get_route_supply,
)
from generate_gtfs_fixture import generate_gtfs_fixture


@pytest.fixture(scope="module")
def gtfs_test_dir():
    """Generates a temporary GTFS fixture directory."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        generate_gtfs_fixture(tmp_dir)
        yield tmp_dir


@pytest.fixture(scope="module")
def ingested_db(gtfs_test_dir):
    """Ingests fixture GTFS into a temporary SQLite database."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as db_dir:
        db_path = os.path.join(db_dir, "test_crowdwise.db")
        db_url = f"sqlite:///{db_path}"
        counts = ingest_gtfs_directory(gtfs_test_dir, db_url)
        engine = create_engine(db_url)
        yield engine, counts
        engine.dispose(close=True)


class TestGTFSIngestionIntegration:
    """Integration test suite for GTFS ingestion."""

    def test_ingestion_table_counts_positive(self, ingested_db):
        """Verifies that all 6 compact derived tables have non-zero row counts."""
        _, counts = ingested_db
        expected_tables = [
            "dim_stops",
            "dim_routes",
            "dim_route_patterns",
            "rel_pattern_stops",
            "dim_trip_starts",
            "fact_route_supply",
        ]
        for tbl in expected_tables:
            assert counts[tbl] > 0, f"Table {tbl} has 0 rows after ingestion"

    def test_query_load_all_stops(self, ingested_db):
        """Verifies load_all_stops returns complete stop records with coordinates."""
        engine, _ = ingested_db
        with Session(engine) as s:
            stops = load_all_stops(s)
            assert len(stops) > 100
            first_stop = stops[0]
            assert "stop_id" in first_stop
            assert "stop_lat" in first_stop
            assert "stop_lon" in first_stop

    def test_query_get_stop_sequence(self, ingested_db):
        """Verifies get_stop_sequence returns ordered (sequence, stop_id, zone_id) tuples."""
        engine, _ = ingested_db
        with Session(engine) as s:
            patterns = get_route_patterns("502", s)
            assert len(patterns) >= 1
            p0 = patterns[0]
            pid = p0["pattern_id"]

            # Verify contract columns
            assert "total_dist_km" in p0, "total_dist_km missing from dim_route_patterns"
            assert p0["total_dist_km"] > 0.0, f"total_dist_km should be positive, got {p0['total_dist_km']}"
            assert "num_stops" in p0, "num_stops missing from dim_route_patterns"
            assert p0["num_stops"] == p0["stop_count"]

            seqs = get_stop_sequence(pid, s)
            assert len(seqs) >= 10
            # Sequence numbers must be strictly increasing
            assert [sq[0] for sq in seqs] == list(range(len(seqs)))
            # Zones must be between 0 and 7
            for sq in seqs:
                assert 0 <= sq[2] <= 7

    def test_query_get_stop_sequence_optional_session(self, monkeypatch, ingested_db):
        """Verifies get_stop_sequence can be called without explicit session parameter."""
        engine, _ = ingested_db
        monkeypatch.setenv("CROWDWISE_DB_URL", str(engine.url))
        patterns = get_route_patterns("502")
        assert len(patterns) >= 1
        pid = patterns[0]["pattern_id"]

        # Call get_stop_sequence with only pattern_id
        seqs = get_stop_sequence(pid)
        assert len(seqs) >= 10
        assert [sq[0] for sq in seqs] == list(range(len(seqs)))

    def test_query_get_route_supply(self, ingested_db):
        """Verifies get_route_supply returns valid trips_per_hour and finite headway."""
        engine, _ = ingested_db
        with Session(engine) as s:
            supply = get_route_supply("502", direction_id=0, day_type="WEEKDAY", hour=8, session=s)
            assert supply is not None
            assert supply["trips_per_hour"] > 0
            assert supply["avg_headway_min"] > 0.0
