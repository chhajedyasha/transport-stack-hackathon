"""crowdwise/backend/app/demand/types.py
Data contracts and profiling result structures for ETM pipeline.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Literal

IngestionMode = Literal["mode_a", "mode_b", "mode_c"]


@dataclass
class QualityProfileResult:
    """Diagnostic report emitted by ETMDataProfiler."""
    mode: IngestionMode
    total_records: int
    valid_records: int
    invalid_records: int
    valid_timestamp_rate: float
    time_min: Optional[str]
    time_max: Optional[str]
    null_rates: Dict[str, float]
    unmatched_routes_count: int
    unmatched_routes_rate: float
    quality_pass: bool
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_alighting(self) -> bool:
        return self.mode == "mode_a"

    @property
    def is_aggregated(self) -> bool:
        return self.mode == "mode_c"

    @property
    def future_timestamp_count(self) -> int:
        return self.diagnostics.get("future_timestamps_detected", 0)

    @property
    def negative_fare_count(self) -> int:
        return self.diagnostics.get("negative_fares_detected", 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "valid_timestamp_rate": self.valid_timestamp_rate,
            "time_min": self.time_min,
            "time_max": self.time_max,
            "null_rates": self.null_rates,
            "unmatched_routes_count": self.unmatched_routes_count,
            "unmatched_routes_rate": self.unmatched_routes_rate,
            "quality_pass": self.quality_pass,
            "diagnostics": self.diagnostics,
        }


@dataclass
class NormalizedTicketRecord:
    """Standardized ticket record emitted after profiling and privacy sanitization."""
    ticket_id: str                      # Salted hash if personal, or synthesized ID
    timestamp: datetime                 # UTC datetime truncated to minute precision
    timestamp_iso: str                  # Standard ISO-8601 string (YYYY-MM-DDTHH:MM:SSZ)
    route_id: str                       # Matched or normalized route ID
    direction_id: int                   # 0 = UP, 1 = DOWN
    day_type: str                       # WEEKDAY, SATURDAY, SUNDAY
    hour: int                           # 0 to 23
    boarding_stop_id: Optional[str]     # Populated in Mode A and Mode B
    alighting_stop_id: Optional[str]    # Populated in Mode A only
    passenger_count: int = 1            # Group size or ticket count
    fare_paid: float = 0.0              # Clean numeric monetary fare
    fare_stage: Optional[int] = None    # Distance/fare stage if available
    vendor_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneDemandRecord:
    """Corridor zone-level passenger demand record."""
    trip_id: str
    route_id: str
    direction_id: int
    day_type: str
    trip_date: str
    date: str
    hour: int
    zone_id: int
    mean_load: float
    max_load: int
    boardings_total: int
    alightings_total: int
    trip_count: int = 1
