"""crowdwise/backend/app/models/transit.py
SQLAlchemy 2.0 ORM models for CrowdWise Static Transit Layer.
Supports SQLite (development/demo) with foreign key PRAGMA and PostgreSQL (production).
"""
from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, ForeignKey, Index,
    event, create_engine, Engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    """Base declarative class for CrowdWise ORM models."""
    pass


class DimStop(Base):
    """Physical bus stops in Delhi NCT with coordinates and terminal flags."""
    __tablename__ = "dim_stops"

    stop_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    stop_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    stop_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stop_lat: Mapped[float] = mapped_column(Float, nullable=False)
    stop_lon: Mapped[float] = mapped_column(Float, nullable=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    pattern_stops: Mapped[List["RelPatternStop"]] = relationship("RelPatternStop", back_populates="stop")

    __table_args__ = (
        Index("idx_dim_stops_coords", "stop_lat", "stop_lon"),
    )

    def to_dict(self) -> dict:
        return {
            "stop_id": self.stop_id,
            "stop_code": self.stop_code,
            "stop_name": self.stop_name,
            "stop_lat": self.stop_lat,
            "stop_lon": self.stop_lon,
            "is_terminal": self.is_terminal,
        }


class DimRoute(Base):
    """Public transit routes operated by DTC, DIMTS, or cluster concessionaires."""
    __tablename__ = "dim_routes"

    route_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(32), nullable=False, default="DTC")
    route_short_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    route_long_name: Mapped[str] = mapped_column(String(255), nullable=False)
    route_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    patterns: Mapped[List["DimRoutePattern"]] = relationship("DimRoutePattern", back_populates="route")
    supply_records: Mapped[List["FactRouteSupply"]] = relationship("FactRouteSupply", back_populates="route")

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "agency_id": self.agency_id,
            "route_short_name": self.route_short_name,
            "route_long_name": self.route_long_name,
            "route_desc": self.route_desc,
        }


class DimRoutePattern(Base):
    """Distinct physical stop sequences per route and travel direction."""
    __tablename__ = "dim_route_patterns"

    pattern_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_routes.route_id"), nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = UP, 1 = DOWN
    stop_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_dist_km: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)
    start_stop_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_stops.stop_id"), nullable=False)
    end_stop_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_stops.stop_id"), nullable=False)
    shape_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    @property
    def num_stops(self) -> int:
        """Compatibility alias for stop_count per PROJECT.md interface contract."""
        return self.stop_count

    @num_stops.setter
    def num_stops(self, value: int) -> None:
        self.stop_count = value

    # Relationships
    route: Mapped["DimRoute"] = relationship("DimRoute", back_populates="patterns")
    start_stop: Mapped["DimStop"] = relationship("DimStop", foreign_keys=[start_stop_id])
    end_stop: Mapped["DimStop"] = relationship("DimStop", foreign_keys=[end_stop_id])
    pattern_stops: Mapped[List["RelPatternStop"]] = relationship(
        "RelPatternStop",
        back_populates="pattern",
        order_by="RelPatternStop.stop_sequence",
        cascade="all, delete-orphan",
    )
    trip_starts: Mapped[List["DimTripStart"]] = relationship("DimTripStart", back_populates="pattern")

    __table_args__ = (
        Index("idx_patterns_route_dir", "route_id", "direction_id"),
    )

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "route_id": self.route_id,
            "direction_id": self.direction_id,
            "stop_count": self.stop_count,
            "num_stops": self.stop_count,
            "total_dist_km": self.total_dist_km,
            "start_stop_id": self.start_stop_id,
            "end_stop_id": self.end_stop_id,
            "shape_id": self.shape_id,
        }


class RelPatternStop(Base):
    """Ordered stops along each pattern sequence with 8-zone IDs and cumulative distances."""
    __tablename__ = "rel_pattern_stops"

    pattern_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dim_route_patterns.pattern_id"), primary_key=True
    )
    stop_sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    stop_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_stops.stop_id"), nullable=False)
    zone_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 to 7
    cum_dist_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Relationships
    pattern: Mapped["DimRoutePattern"] = relationship("DimRoutePattern", back_populates="pattern_stops")
    stop: Mapped["DimStop"] = relationship("DimStop", back_populates="pattern_stops")

    __table_args__ = (
        Index("idx_pattern_stops_stop", "stop_id", "pattern_id"),
        Index("idx_pattern_stops_zone", "pattern_id", "zone_id"),
    )

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "stop_sequence": self.stop_sequence,
            "stop_id": self.stop_id,
            "zone_id": self.zone_id,
            "cum_dist_km": self.cum_dist_km,
        }


class DimTripStart(Base):
    """Trip departure schedules by pattern and operating calendar day type."""
    __tablename__ = "dim_trip_starts"

    trip_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_routes.route_id"), nullable=False)
    pattern_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("dim_route_patterns.pattern_id"), nullable=False
    )
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 or 1
    service_id: Mapped[str] = mapped_column(String(32), nullable=False)
    departure_time: Mapped[str] = mapped_column(String(8), nullable=False)  # "HH:MM:SS"
    departure_hour: Mapped[int] = mapped_column(Integer, nullable=False)    # 0 to 23
    day_type: Mapped[str] = mapped_column(String(16), nullable=False)       # "WEEKDAY", "SATURDAY", "SUNDAY"

    # Relationships
    pattern: Mapped["DimRoutePattern"] = relationship("DimRoutePattern", back_populates="trip_starts")

    __table_args__ = (
        Index("idx_trip_starts_lookup", "pattern_id", "day_type", "departure_hour"),
        Index("idx_trip_starts_route", "route_id", "direction_id", "day_type"),
    )

    def to_dict(self) -> dict:
        return {
            "trip_id": self.trip_id,
            "route_id": self.route_id,
            "pattern_id": self.pattern_id,
            "direction_id": self.direction_id,
            "service_id": self.service_id,
            "departure_time": self.departure_time,
            "departure_hour": self.departure_hour,
            "day_type": self.day_type,
        }


class FactRouteSupply(Base):
    """Aggregated scheduled transit supply (trips per hour and average headway)."""
    __tablename__ = "fact_route_supply"

    route_id: Mapped[str] = mapped_column(String(64), ForeignKey("dim_routes.route_id"), primary_key=True)
    direction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    hour: Mapped[int] = mapped_column(Integer, primary_key=True)  # 0 to 23
    trips_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_headway_min: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    route: Mapped["DimRoute"] = relationship("DimRoute", back_populates="supply_records")

    __table_args__ = (
        Index("idx_route_supply_query", "route_id", "direction_id", "day_type", "hour"),
    )

    def to_dict(self) -> dict:
        return {
            "route_id": self.route_id,
            "direction_id": self.direction_id,
            "day_type": self.day_type,
            "hour": self.hour,
            "trips_per_hour": self.trips_per_hour,
            "avg_headway_min": self.avg_headway_min,
        }


# ---------------------------------------------------------------------------
# Database connection and helper functions
# ---------------------------------------------------------------------------

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforces SQLite foreign keys for referential integrity."""
    # Only execute pragma on sqlite connections
    if dbapi_connection.__class__.__module__.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass
        finally:
            cursor.close()


def get_engine(db_url: str, echo: bool = False) -> Engine:
    """Creates a SQLAlchemy engine for SQLite or PostgreSQL."""
    return create_engine(db_url, echo=echo)


def get_session_factory(engine: Engine):
    """Returns a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_all_tables(engine: Engine) -> None:
    """Creates all 6 compact derived tables in the target database."""
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine: Engine) -> None:
    """Drops all tables from target database."""
    Base.metadata.drop_all(bind=engine)
