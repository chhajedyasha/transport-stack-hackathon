"""crowdwise/backend/app/services/direction_resolver.py
Deterministic 4-level directionality resolution engine for Delhi GTFS feeds.

Hierarchy:
1. Explicit direction_id in GTFS trips.txt (0 or 1).
2. Route name regex matching UP / DOWN / STL / LSTL / (+/-) / OUTBOUND / INBOUND.
3. Trip ID suffix and token inspection.
4. Geographic bearing vector & polygon curvature fallback (with circular loop detection).

Guarantees 100% resolution with zero unassigned directions across all routes.
"""
import math
import re
from typing import List, Tuple, Optional, Union, Any

# Earth radius in kilometers (WGS-84 volumetric mean)
R_EARTH_KM = 6371.0088

# Level 2 Regex Patterns for Route Short Name / Long Name / Headsign
REGEX_DIR_0 = re.compile(
    r'(?:'
    r'(?<=[0-9A-Z])UP\b|'
    r'(?:^|[\s_\-/])(?:UP|OUTBOUND|ONWARD|OUT|CLW|CLOCKWISE)(?:[\s_\-/]|$)|'
    r'\(\+\)|'
    r'(?:^|[\s_\-/])PLUS(?:[\s_\-/]|$)'
    r')',
    re.IGNORECASE
)

REGEX_DIR_1 = re.compile(
    r'(?:'
    r'(?<=[0-9A-Z])(?:DOWN|DN)\b|'
    r'(?:^|[\s_\-/])(?:DOWN|DN|INBOUND|RETURN|IN|CCLW|COUNTERCLOCKWISE)(?:[\s_\-/]|$)|'
    r'\(\-\)|'
    r'(?:^|[\s_\-/])MINUS(?:[\s_\-/]|$)'
    r')',
    re.IGNORECASE
)

# Level 3 Regex Patterns for trip_id tokens
REGEX_TRIP_DIR_0 = re.compile(
    r'(?:[_\-/]|^)(?:UP|OUT|OUTBOUND|DIR0|D0|0)(?=[_\-/]|$)',
    re.IGNORECASE
)

REGEX_TRIP_DIR_1 = re.compile(
    r'(?:[_\-/]|^)(?:DOWN|DN|IN|INBOUND|DIR1|D1|1)(?=[_\-/]|$)',
    re.IGNORECASE
)


def compute_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two points in kilometers."""
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    dphi = phi2 - phi1
    dlam = lam2 - lam1

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * R_EARTH_KM * math.asin(math.sqrt(max(0.0, min(1.0, a))))


def compute_forward_azimuth(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes forward azimuth (bearing) from point 1 to point 2 in degrees [0, 360)."""
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    dlam = lam2 - lam1

    y = math.sin(dlam) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
    theta = math.degrees(math.atan2(y, x))
    return (theta + 360.0) % 360.0


def compute_polygon_signed_area(coords: List[Tuple[float, float]]) -> float:
    """Computes signed area of a coordinate sequence using shoelace formula.
    Positive area implies Counter-Clockwise (CCW); negative implies Clockwise (CW).
    """
    if len(coords) < 3:
        return 0.0

    mean_lat = sum(c[0] for c in coords) / len(coords)
    mean_lon = sum(c[1] for c in coords) / len(coords)
    rad_lat = math.radians(mean_lat)

    # Project to flat km coordinates
    pts = [
        (
            R_EARTH_KM * math.radians(c[1] - mean_lon) * math.cos(rad_lat),
            R_EARTH_KM * math.radians(c[0] - mean_lat)
        )
        for c in coords
    ]

    area = 0.0
    for i in range(len(pts) - 1):
        area += pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1]
    return 0.5 * area


def resolve_direction_from_coords(coords: List[Tuple[float, float]]) -> int:
    """Level 4: Determines direction from ordered list of (lat, lon) coordinates."""
    if not coords or len(coords) < 2:
        return 0  # Deterministic default

    start_lat, start_lon = coords[0]
    end_lat, end_lon = coords[-1]
    end_dist = compute_haversine_distance(start_lat, start_lon, end_lat, end_lon)

    # Case 4B: Circular Loop Route (start and end stops < 500 meters apart)
    if end_dist < 0.50:
        # Check signed area (curvature) first if 3+ stops
        if len(coords) >= 3:
            signed_area = compute_polygon_signed_area(coords)
            if abs(signed_area) > 0.01:
                # CCW (area >= 0) -> 0; CW (area < 0) -> 1
                return 0 if signed_area >= 0 else 1

        # Fallback to apex stop bearing
        max_dist = -1.0
        apex_idx = 0
        for i, (lat, lon) in enumerate(coords):
            d = compute_haversine_distance(start_lat, start_lon, lat, lon)
            if d > max_dist:
                max_dist = d
                apex_idx = i

        if apex_idx > 0 and max_dist > 0.1:
            apex_azimuth = compute_forward_azimuth(start_lat, start_lon, coords[apex_idx][0], coords[apex_idx][1])
            return 0 if 0.0 <= apex_azimuth < 180.0 else 1

    # Case 4A: Non-Circular Route
    azimuth = compute_forward_azimuth(start_lat, start_lon, end_lat, end_lon)
    return 0 if 0.0 <= azimuth < 180.0 else 1


def resolve_direction(
    explicit_direction_id: Optional[Union[int, str, float]] = None,
    route_short_name: Optional[str] = None,
    route_long_name: Optional[str] = None,
    trip_id: Optional[str] = None,
    trip_headsign: Optional[str] = None,
    stop_coords: Optional[List[Tuple[float, float]]] = None,
) -> int:
    """Resolves route-trip directionality using the deterministic 4-level hierarchy.

    Args:
        explicit_direction_id: Value from trips.txt (e.g. 0, 1, '0', '1', None).
        route_short_name: Route short name (e.g. '102AUP', '761DOWN').
        route_long_name: Route long name / corridor description.
        trip_id: Unique trip identifier string.
        trip_headsign: Trip destination headsign.
        stop_coords: Ordered list of (lat, lon) coordinates for pattern stops.

    Returns:
        0 (UP / Outbound / CCW) or 1 (DOWN / Inbound / CW). Never returns None.
    """
    # -------------------------------------------------------------
    # Level 1: Explicit GTFS direction_id
    # -------------------------------------------------------------
    if explicit_direction_id is not None:
        try:
            val_str = str(explicit_direction_id).strip()
            if val_str in ("0", "1"):
                return int(val_str)
            val_float = float(val_str)
            if val_float in (0.0, 1.0):
                return int(val_float)
        except (ValueError, TypeError):
            pass

    # -------------------------------------------------------------
    # Level 2: Route Name Regular Expression Matching
    # -------------------------------------------------------------
    names_to_check = [name for name in [route_short_name, route_long_name, trip_headsign] if name]
    for name in names_to_check:
        clean_name = name.strip()
        is_dir_0 = bool(REGEX_DIR_0.search(clean_name))
        is_dir_1 = bool(REGEX_DIR_1.search(clean_name))

        if is_dir_0 and not is_dir_1:
            return 0
        if is_dir_1 and not is_dir_0:
            return 1

    # -------------------------------------------------------------
    # Level 3: Trip ID Suffix & Delimiter Inspection
    # -------------------------------------------------------------
    if trip_id:
        clean_trip_id = trip_id.strip()
        trip_is_dir_0 = bool(REGEX_TRIP_DIR_0.search(clean_trip_id))
        trip_is_dir_1 = bool(REGEX_TRIP_DIR_1.search(clean_trip_id))

        if trip_is_dir_0 and not trip_is_dir_1:
            return 0
        if trip_is_dir_1 and not trip_is_dir_0:
            return 1

    # -------------------------------------------------------------
    # Level 4: Geographic Bearing & Polygon Curvature Fallback
    # -------------------------------------------------------------
    if stop_coords and len(stop_coords) >= 2:
        return resolve_direction_from_coords(stop_coords)

    # Deterministic terminal fallback
    return 0
