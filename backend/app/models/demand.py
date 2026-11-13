"""crowdwise/backend/app/models/demand.py
SQLAlchemy 2.0 ORM models for ETM Staging, Zone Demand Facts, and System Runtime Metadata.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Float, DateTime, func, Index
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.transit import Base


class SysRuntimeMetadata(Base):
    """System runtime configuration metadata and active data tier flag."""
    __tablename__ = "sys_runtime_metadata"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value}


class EtmStagingTicket(Base):
    """Isolated staging table for ingested and anonymized ETM tickets."""
    __tablename__ = "etm_staging_tickets"

    staging_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    boarding_stop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    alighting_stop_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    passenger_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    fare_paid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    smartcard_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_staging_route_dir", "route_id", "direction_id"),
    )


class FactZoneDemand(Base):
    """Reconstructed passenger demand and crowdedness facts aggregated into 8 contiguous zones."""
    __tablename__ = "fact_zone_demand"

    demand_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    day_type: Mapped[str] = mapped_column(String(16), nullable=False)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 to 7
    trip_date: Mapped[str] = mapped_column(String(10), nullable=False)
    mean_load: Mapped[float] = mapped_column(Float, nullable=False)
    max_load: Mapped[int] = mapped_column(Integer, nullable=False)
    boardings_total: Mapped[int] = mapped_column(Integer, nullable=False)
    alightings_total: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    data_tier: Mapped[str] = mapped_column(String(32), default="organizer", nullable=False)

    __table_args__ = (
        Index("idx_fact_demand_lookup", "route_id", "direction_id", "day_type", "hour", "zone_id"),
    )


class FactZoneDemandStaging(Base):
    """Isolated staging table for reconstructed zone demand facts during atomic swap."""
    __tablename__ = "fact_zone_demand_staging"

    demand_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[str] = mapped_column(String(64), nullable=False)
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    day_type: Mapped[str] = mapped_column(String(16), nullable=False)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)
    zone_id: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_date: Mapped[str] = mapped_column(String(10), nullable=False)
    mean_load: Mapped[float] = mapped_column(Float, nullable=False)
    max_load: Mapped[int] = mapped_column(Integer, nullable=False)
    boardings_total: Mapped[int] = mapped_column(Integer, nullable=False)
    alightings_total: Mapped[int] = mapped_column(Integer, nullable=False)
    trip_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    data_tier: Mapped[str] = mapped_column(String(32), default="organizer", nullable=False)

    __table_args__ = (
        Index("idx_staging_demand_lookup", "route_id", "direction_id", "day_type", "hour", "zone_id"),
    )
