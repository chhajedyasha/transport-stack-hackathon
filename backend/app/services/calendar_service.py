"""crowdwise/backend/app/services/calendar_service.py
Service calendar mapping and 24-hour timestamp normalization for Delhi GTFS feeds.

Features:
- Maps calendar.txt 7-day boolean schedules to canonical {'WEEKDAY', 'SATURDAY', 'SUNDAY'}.
- Integrates calendar_dates.txt exception overrides (type 1: added, type 2: removed).
- Normalizes post-midnight trips (hours >= 24) to seconds and modular 0..23 hour bands.
"""
import datetime
import logging
from typing import Dict, Set, Tuple, Any, Optional
import pandas as pd

logger = logging.getLogger("crowdwise.calendar_service")

CANONICAL_DAY_TYPES: Set[str] = {"WEEKDAY", "SATURDAY", "SUNDAY"}


def parse_gtfs_time_to_seconds(time_str: str) -> Tuple[int, int, str, bool]:
    """Parses GTFS HH:MM:SS time string, handling hours >= 24 gracefully.

    Args:
        time_str: GTFS formatted time string (e.g. '08:30:00', '24:15:00', '25:45:10').

    Returns:
        Tuple of:
        - total_seconds: integer seconds past midnight (can exceed 86400)
        - normalized_hour: integer hour in range [0, 23]
        - normalized_time_str: string formatted as 'HH:MM:SS' in range [00:00:00, 23:59:59]
        - is_next_day_rollover: boolean indicating if original hour was >= 24
    """
    parts = str(time_str).strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid GTFS time format: '{time_str}'")

    h = int(parts[0])
    m = int(parts[1])
    s = int(parts[2]) if len(parts) > 2 else 0

    total_seconds = h * 3600 + m * 60 + s
    is_rollover = h >= 24 or total_seconds >= 86400

    norm_h = h % 24
    norm_time_str = f"{norm_h:02d}:{m:02d}:{s:02d}"

    return total_seconds, norm_h, norm_time_str, is_rollover


def map_calendar_row(row: Dict[str, Any]) -> Set[str]:
    """Maps a single calendar.txt row to a set of canonical day types.

    Args:
        row: Dict with keys ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].

    Returns:
        Set containing a subset of {'WEEKDAY', 'SATURDAY', 'SUNDAY'}.
    """
    day_types = set()

    # Weekday check (Mon-Fri)
    weekday_flags = [
        int(row.get("monday", 0)),
        int(row.get("tuesday", 0)),
        int(row.get("wednesday", 0)),
        int(row.get("thursday", 0)),
        int(row.get("friday", 0)),
    ]
    if any(weekday_flags):
        day_types.add("WEEKDAY")

    # Saturday check
    if int(row.get("saturday", 0)) == 1:
        day_types.add("SATURDAY")

    # Sunday check
    if int(row.get("sunday", 0)) == 1:
        day_types.add("SUNDAY")

    return day_types


def build_service_calendar_map(
    calendar_df: Optional[pd.DataFrame] = None,
    calendar_dates_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Set[str]]:
    """Builds a lookup mapping service_id -> set of active canonical day types.

    Args:
        calendar_df: DataFrame of calendar.txt (service_id, monday, ..., sunday).
        calendar_dates_df: Optional DataFrame of calendar_dates.txt (service_id, date, exception_type).

    Returns:
        Dict mapping service_id string -> Set[str] of {'WEEKDAY', 'SATURDAY', 'SUNDAY'}.
    """
    service_map: Dict[str, Set[str]] = {}
    regular_service_map: Dict[str, Set[str]] = {}

    # 1. Process calendar.txt
    if calendar_df is not None and not calendar_df.empty:
        for row in calendar_df.itertuples(index=False):
            srv_id = str(row.service_id).strip()
            row_dict = row._asdict() if hasattr(row, "_asdict") else {
                "monday": getattr(row, "monday", 0),
                "tuesday": getattr(row, "tuesday", 0),
                "wednesday": getattr(row, "wednesday", 0),
                "thursday": getattr(row, "thursday", 0),
                "friday": getattr(row, "friday", 0),
                "saturday": getattr(row, "saturday", 0),
                "sunday": getattr(row, "sunday", 0),
            }
            active_days = map_calendar_row(row_dict)
            service_map[srv_id] = set(active_days)
            regular_service_map[srv_id] = set(active_days)

    # 2. Process calendar_dates.txt exceptions if present
    if calendar_dates_df is not None and not calendar_dates_df.empty:
        for row in calendar_dates_df.itertuples(index=False):
            srv_id = str(row.service_id).strip()
            date_str = str(row.date).strip()
            exc_type = int(getattr(row, "exception_type", 1))

            try:
                dt = datetime.datetime.strptime(date_str, "%Y%m%d").date()
                weekday_idx = dt.weekday()  # Mon=0, Sun=6
                if weekday_idx < 5:
                    target_day = "WEEKDAY"
                elif weekday_idx == 5:
                    target_day = "SATURDAY"
                else:
                    target_day = "SUNDAY"

                if srv_id not in service_map:
                    service_map[srv_id] = set()

                if exc_type == 1:  # Service added on this date
                    service_map[srv_id].add(target_day)
                elif exc_type == 2:  # Service removed on this date
                    # Single holiday/date cancellation does NOT permanently delete
                    # target_day from regular recurring weekly schedule
                    if srv_id not in regular_service_map or target_day not in regular_service_map[srv_id]:
                        service_map[srv_id].discard(target_day)
            except Exception as e:
                logger.warning(f"Error parsing calendar exception row: {e}")
                continue

    # 3. Fallback for services with zero active day types defined
    for srv_id, days in list(service_map.items()):
        if not days:
            # If service defined but completely empty after both calendar and calendar_dates,
            # default to all canonical day types to avoid silent route loss
            service_map[srv_id] = set(CANONICAL_DAY_TYPES)

    return service_map


def get_day_types_for_service(
    service_id: str,
    service_map: Dict[str, Set[str]],
) -> Set[str]:
    """Retrieves active canonical day types for a service_id with fallback to all days."""
    srv_clean = str(service_id).strip()
    if srv_clean in service_map and service_map[srv_clean]:
        return service_map[srv_clean]
    # Fallback heuristic: all day types
    return set(CANONICAL_DAY_TYPES)
