"""crowdwise/backend/tests/conftest.py
Pytest fixtures for CrowdWise static transit layer unit tests.
"""
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add backend directory and crowdwise root to sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
crowdwise_dir = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, crowdwise_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.models.transit import Base, DimStop, DimRoute, DimRoutePattern, RelPatternStop, DimTripStart, FactRouteSupply


@pytest.fixture
def sqlite_engine():
    """Provides an in-memory SQLite engine with PRAGMA foreign_keys = ON."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Provides a transactional SQLAlchemy session bound to the in-memory engine."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def sample_stops(db_session):
    """Seeds 5 physical bus stops in Delhi NCT."""
    stops = [
        DimStop(stop_id="ST_01", stop_code="DEL001", stop_name="Mehrauli Terminal", stop_lat=28.5180, stop_lon=77.1810, is_terminal=True),
        DimStop(stop_id="ST_02", stop_code="DEL002", stop_name="AIIMS Metro Station", stop_lat=28.5670, stop_lon=77.2100, is_terminal=False),
        DimStop(stop_id="ST_03", stop_code="DEL003", stop_name="Connaught Place (Super Bazar)", stop_lat=28.6328, stop_lon=77.2195, is_terminal=False),
        DimStop(stop_id="ST_04", stop_code="DEL004", stop_name="ISBT Kashmere Gate", stop_lat=28.6675, stop_lon=77.2285, is_terminal=True),
        DimStop(stop_id="ST_05", stop_code="DEL005", stop_name="Anand Vihar ISBT", stop_lat=28.6465, stop_lon=77.3150, is_terminal=True),
    ]
    db_session.add_all(stops)
    db_session.commit()
    return stops


@pytest.fixture
def sample_routes(db_session):
    """Seeds sample routes."""
    routes = [
        DimRoute(route_id="502", agency_id="DTC", route_short_name="502UP", route_long_name="Mehrauli to Kashmere Gate"),
        DimRoute(route_id="TMS", agency_id="DTC", route_short_name="TMS (+)", route_long_name="Mudrika Ring Road Inner Circle"),
    ]
    db_session.add_all(routes)
    db_session.commit()
    return routes
