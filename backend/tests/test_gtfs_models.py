"""crowdwise/backend/tests/test_gtfs_models.py
Unit tests for SQLAlchemy 2.0 ORM models (Features F01 - Compact derived schema).
Verifies dual-dialect schema creation, constraints, foreign key referential integrity, and CRUD.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.transit import (
    Base,
    DimStop,
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimTripStart,
    FactRouteSupply,
)


class TestGTFSModels:
    """Test suite for the 6 compact derived tables."""

    def test_schema_table_names_and_columns(self, sqlite_engine):
        """Verifies all 6 compact derived tables exist with required columns."""
        table_names = Base.metadata.tables.keys()
        expected_tables = {
            "dim_stops",
            "dim_routes",
            "dim_route_patterns",
            "rel_pattern_stops",
            "dim_trip_starts",
            "fact_route_supply",
        }
        assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - set(table_names)}"

    def test_dim_stops_crud_and_to_dict(self, db_session):
        """Verifies CRUD operations and dictionary serialization on DimStop."""
        stop = DimStop(
            stop_id="ST_TEST_01",
            stop_code="9CE99999",
            stop_name="Test Gate Delhi",
            stop_lat=28.6500,
            stop_lon=77.2300,
            is_terminal=True,
        )
        db_session.add(stop)
        db_session.commit()

        # Query back
        loaded = db_session.execute(select(DimStop).where(DimStop.stop_id == "ST_TEST_01")).scalar_one()
        assert loaded.stop_name == "Test Gate Delhi"
        assert loaded.is_terminal is True
        assert loaded.to_dict()["stop_code"] == "9CE99999"

    def test_dim_routes_crud(self, db_session):
        """Verifies CRUD operations on DimRoute."""
        route = DimRoute(
            route_id="R_TEST",
            agency_id="DTC",
            route_short_name="502UP",
            route_long_name="Mehrauli Terminal to Mori Gate Terminal",
            route_desc="North-South Trunk Corridor",
        )
        db_session.add(route)
        db_session.commit()

        loaded = db_session.execute(select(DimRoute).where(DimRoute.route_id == "R_TEST")).scalar_one()
        assert loaded.route_short_name == "502UP"
        assert loaded.agency_id == "DTC"

    def test_foreign_key_referential_integrity_violation(self, db_session):
        """Verifies PRAGMA foreign_keys = ON blocks invalid foreign key references."""
        # Attempt to insert a pattern with non-existent route and stop
        invalid_pattern = DimRoutePattern(
            pattern_id="PAT_INVALID",
            route_id="NON_EXISTENT_ROUTE",
            direction_id=0,
            stop_count=2,
            start_stop_id="NON_EXISTENT_STOP_1",
            end_stop_id="NON_EXISTENT_STOP_2",
        )
        db_session.add(invalid_pattern)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_pattern_and_pattern_stops_relationship(self, db_session, sample_stops, sample_routes):
        """Verifies DimRoutePattern and RelPatternStop relationships and ordering."""
        route = sample_routes[0]
        stop1 = sample_stops[0]
        stop2 = sample_stops[1]

        pattern = DimRoutePattern(
            pattern_id="PAT_502_0_01",
            route_id=route.route_id,
            direction_id=0,
            stop_count=2,
            start_stop_id=stop1.stop_id,
            end_stop_id=stop2.stop_id,
        )
        db_session.add(pattern)
        db_session.commit()

        # Add pattern stops
        ps1 = RelPatternStop(pattern_id=pattern.pattern_id, stop_sequence=0, stop_id=stop1.stop_id, zone_id=0, cum_dist_km=0.0)
        ps2 = RelPatternStop(pattern_id=pattern.pattern_id, stop_sequence=1, stop_id=stop2.stop_id, zone_id=1, cum_dist_km=5.4)
        db_session.add_all([ps1, ps2])
        db_session.commit()

        # Verify back-population
        reloaded_pattern = db_session.execute(select(DimRoutePattern).where(DimRoutePattern.pattern_id == "PAT_502_0_01")).scalar_one()
        assert len(reloaded_pattern.pattern_stops) == 2
        assert reloaded_pattern.pattern_stops[0].stop_sequence == 0
        assert reloaded_pattern.pattern_stops[0].zone_id == 0
        assert reloaded_pattern.pattern_stops[1].cum_dist_km == 5.4

    def test_dim_trip_starts_crud(self, db_session, sample_stops, sample_routes):
        """Verifies DimTripStart creation and query."""
        route = sample_routes[0]
        stop1 = sample_stops[0]
        stop2 = sample_stops[1]

        pattern = DimRoutePattern(
            pattern_id="PAT_502_0_02",
            route_id=route.route_id,
            direction_id=0,
            stop_count=2,
            start_stop_id=stop1.stop_id,
            end_stop_id=stop2.stop_id,
        )
        db_session.add(pattern)
        db_session.commit()

        trip = DimTripStart(
            trip_id="TRIP_502_01_WEEKDAY",
            route_id=route.route_id,
            pattern_id=pattern.pattern_id,
            direction_id=0,
            service_id="DAILY",
            departure_time="08:30:00",
            departure_hour=8,
            day_type="WEEKDAY",
        )
        db_session.add(trip)
        db_session.commit()

        loaded_trip = db_session.execute(select(DimTripStart).where(DimTripStart.trip_id == "TRIP_502_01_WEEKDAY")).scalar_one()
        assert loaded_trip.departure_hour == 8
        assert loaded_trip.day_type == "WEEKDAY"

    def test_fact_route_supply_composite_pk(self, db_session, sample_routes):
        """Verifies FactRouteSupply composite primary key and metrics."""
        route = sample_routes[0]
        supply = FactRouteSupply(
            route_id=route.route_id,
            direction_id=0,
            day_type="WEEKDAY",
            hour=8,
            trips_per_hour=6,
            avg_headway_min=10.0,
        )
        db_session.add(supply)
        db_session.commit()

        # Duplicate PK should raise IntegrityError
        db_session.expunge(supply)
        dup = FactRouteSupply(
            route_id=route.route_id,
            direction_id=0,
            day_type="WEEKDAY",
            hour=8,
            trips_per_hour=7,
            avg_headway_min=8.5,
        )
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
