"""crowdwise/backend/tests/test_direction_calendar.py
Unit tests for Directionality Resolution (F02) and Day Type Mapping (F03).
Verifies 100% resolution invariant, zero missing directions, and edge-case handling.
"""
import pytest
import pandas as pd
from app.services.direction_resolver import (
    resolve_direction,
    compute_haversine_distance,
    compute_forward_azimuth,
    compute_polygon_signed_area,
    resolve_direction_from_coords,
)
from app.services.calendar_service import (
    parse_gtfs_time_to_seconds,
    map_calendar_row,
    build_service_calendar_map,
    get_day_types_for_service,
    CANONICAL_DAY_TYPES,
)


class TestDirectionalityResolution:
    """F02: Route Directionality Resolution hierarchy."""

    def test_level1_explicit_direction_integers(self):
        """Verifies explicit direction_id 0 and 1 are returned directly."""
        assert resolve_direction(explicit_direction_id=0) == 0
        assert resolve_direction(explicit_direction_id=1) == 1

    def test_level1_explicit_direction_strings_and_floats(self):
        """Verifies string and float representations of 0 and 1 are parsed correctly."""
        assert resolve_direction(explicit_direction_id="0") == 0
        assert resolve_direction(explicit_direction_id="1") == 1
        assert resolve_direction(explicit_direction_id=0.0) == 0
        assert resolve_direction(explicit_direction_id=1.0) == 1

    def test_level1_invalid_falls_through_to_level2(self):
        """Verifies None, empty string, or invalid numbers fall through to name matching."""
        assert resolve_direction(explicit_direction_id=None, route_short_name="102AUP") == 0
        assert resolve_direction(explicit_direction_id="", route_short_name="102ADOWN") == 1
        assert resolve_direction(explicit_direction_id=-1, route_short_name="502UP") == 0

    def test_level2_route_short_name_suffixes(self):
        """Verifies UP and DOWN suffixes in short route names."""
        assert resolve_direction(route_short_name="102AUP") == 0
        assert resolve_direction(route_short_name="102ADOWN") == 1
        assert resolve_direction(route_short_name="761UP") == 0
        assert resolve_direction(route_short_name="761DOWN") == 1
        assert resolve_direction(route_short_name="761DN") == 1

    def test_level2_short_turn_and_loop_variants(self):
        """Verifies STL and LSTL short-turn loop variants resolve direction cleanly."""
        assert resolve_direction(route_short_name="102LSTLUP") == 0
        assert resolve_direction(route_short_name="102LSTLDOWN") == 1
        assert resolve_direction(route_short_name="534STLUP") == 0
        assert resolve_direction(route_short_name="534STLDOWN") == 1

    def test_level2_ring_road_polarity_and_delimiters(self):
        """Verifies ring road Mudrika (+)/(-) and space/hyphen delimiters."""
        assert resolve_direction(route_short_name="TMS (+)") == 0
        assert resolve_direction(route_short_name="TMS (-)") == 1
        assert resolve_direction(route_short_name="OMS (+)") == 0
        assert resolve_direction(route_short_name="OMS (-)") == 1
        assert resolve_direction(route_short_name="GL-22 UP") == 0
        assert resolve_direction(route_short_name="GL-22 DOWN") == 1

    def test_interface_contract_positional_arguments(self):
        """Verifies resolve_direction(route_name, trip_id) positional contract per PROJECT.md M1<->M2."""
        assert resolve_direction("502DOWN", "TRIP_01") == 1
        assert resolve_direction("502UP", "TRIP_01") == 0
        assert resolve_direction("101DOWN", "TRIP_02") == 1
        assert resolve_direction("101UP", "TRIP_02") == 0
        assert resolve_direction("GL-22 DOWN", "TRIP_03") == 1
        assert resolve_direction("GL-22 UP", "TRIP_03") == 0

    def test_level2_loop_orientation_reconciliation(self):
        """Verifies CLW -> 1 and CCLW -> 0 matching Level 4 shoelace curvature."""
        assert resolve_direction(route_short_name="TMS CLW") == 1
        assert resolve_direction(route_short_name="TMS CCLW") == 0
        assert resolve_direction(route_short_name="OMS CLW") == 1
        assert resolve_direction(route_short_name="OMS CCLW") == 0
        assert resolve_direction(route_short_name="101CLW") == 1
        assert resolve_direction(route_short_name="101CCLW") == 0

    def test_level2_delimiters_parentheses_and_brackets(self):
        """Verifies parentheses and brackets delimiters for UP, DOWN, DN, INBOUND."""
        assert resolve_direction(route_short_name="502 (DOWN)") == 1
        assert resolve_direction(route_short_name="502 [DOWN]") == 1
        assert resolve_direction(route_short_name="502 (UP)") == 0
        assert resolve_direction(route_short_name="502 [UP]") == 0
        assert resolve_direction(route_short_name="502 (DN)") == 1
        assert resolve_direction(route_short_name="502 (INBOUND)") == 1

    def test_level2_natural_language_word_boundary_group(self):
        """Verifies words like GROUP do not trigger false positive UP matching."""
        southbound_coords = [(28.70, 77.20), (28.50, 77.20)]
        res = resolve_direction(
            route_short_name="502",
            trip_headsign="DWARKA SECTOR 10 TO GROUP HOUSING SOCIETY",
            stop_coords=southbound_coords,
        )
        assert res == 1, f"Expected Direction 1 for southbound trip, got {res}"

    def test_level3_trip_id_tokens(self):
        """Verifies trip_id tokens resolve when route name lacks direction cues."""
        assert resolve_direction(route_short_name="502", trip_id="DL_502_UP_0615") == 0
        assert resolve_direction(route_short_name="502", trip_id="DL_502_DN_0615") == 1
        assert resolve_direction(route_short_name="729", trip_id="TRIP_729_DOWN_14") == 1
        assert resolve_direction(route_short_name="729", trip_id="TRIP_729_0_0830") == 0
        assert resolve_direction(route_short_name="729", trip_id="TRIP_729_1_0830") == 1

    def test_level4_geographic_bearing_vector(self):
        """Verifies forward azimuth bearing vector resolves non-circular trajectories."""
        # North-East trajectory: lat increases, lon increases (Azimuth ~45 deg -> Dir 0)
        ne_coords = [(28.50, 77.10), (28.70, 77.20)]
        assert resolve_direction(stop_coords=ne_coords) == 0

        # South-West trajectory: lat decreases, lon decreases (Azimuth ~225 deg -> Dir 1)
        sw_coords = [(28.70, 77.20), (28.50, 77.10)]
        assert resolve_direction(stop_coords=sw_coords) == 1

        # Due East: Azimuth 90 deg -> Dir 0
        east_coords = [(28.60, 77.10), (28.60, 77.30)]
        assert resolve_direction(stop_coords=east_coords) == 0

        # Due West: Azimuth 270 deg -> Dir 1
        west_coords = [(28.60, 77.30), (28.60, 77.10)]
        assert resolve_direction(stop_coords=west_coords) == 1

    def test_level4_circular_loop_shoelace_curvature(self):
        """Verifies circular routes with identical start and end stops resolve via Shoelace curvature."""
        # Counter-Clockwise (CCW) polygon in Delhi NCT -> Dir 0
        ccw_coords = [
            (28.60, 77.20),  # Start
            (28.60, 77.25),  # East
            (28.65, 77.25),  # North
            (28.65, 77.20),  # West
            (28.60, 77.20),  # Return to start (<50m apart)
        ]
        assert resolve_direction_from_coords(ccw_coords) == 0

        # Clockwise (CW) polygon in Delhi NCT -> Dir 1
        cw_coords = [
            (28.60, 77.20),  # Start
            (28.65, 77.20),  # North
            (28.65, 77.25),  # East
            (28.60, 77.25),  # South
            (28.60, 77.20),  # Return to start
        ]
        assert resolve_direction_from_coords(cw_coords) == 1

    def test_zero_unassigned_invariant(self):
        """Verifies resolution function never returns None under arbitrary inputs."""
        test_inputs = [
            ({}, 0),
            ({"explicit_direction_id": "invalid"}, 0),
            ({"route_short_name": "UNKNOWN_ROUTE"}, 0),
            ({"trip_id": "RANDOM_TRIP_XYZ"}, 0),
            ({"stop_coords": []}, 0),
        ]
        for kwargs, _ in test_inputs:
            result = resolve_direction(**kwargs)
            assert result in (0, 1), f"Failed for {kwargs}, got {result}"


class TestDayTypeMappingAndTimestamps:
    """F03: Day Type Mapping and 24h+ Timestamp Normalization."""

    def test_map_calendar_row_weekday(self):
        """Verifies Mon-Fri schedule maps to WEEKDAY."""
        row = {"monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 0, "sunday": 0}
        days = map_calendar_row(row)
        assert days == {"WEEKDAY"}

    def test_map_calendar_row_saturday(self):
        """Verifies Saturday schedule maps to SATURDAY."""
        row = {"monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 1, "sunday": 0}
        assert map_calendar_row(row) == {"SATURDAY"}

    def test_map_calendar_row_sunday(self):
        """Verifies Sunday schedule maps to SUNDAY."""
        row = {"monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 0, "sunday": 1}
        assert map_calendar_row(row) == {"SUNDAY"}

    def test_map_calendar_row_daily_service(self):
        """Verifies daily service maps to all 3 canonical day types."""
        row = {"monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 1, "sunday": 1}
        days = map_calendar_row(row)
        assert days == {"WEEKDAY", "SATURDAY", "SUNDAY"}

    def test_build_service_calendar_map_with_exceptions(self):
        """Verifies calendar_dates.txt exception overrides (type 1: add, type 2: single-date holiday does not purge regular weekly service)."""
        cal_df = pd.DataFrame([
            {"service_id": "S1", "monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 1, "sunday": 0},
            {"service_id": "S2", "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 0, "sunday": 0},
        ])
        # 2026-01-26 is a Monday (holiday) -> exception_type 2 does NOT permanently purge WEEKDAY from regular weekly service S1
        # S2 has all 0s in calendar.txt, but 2026-01-25 (Sunday) is added via exception_type 1
        cal_dates_df = pd.DataFrame([
            {"service_id": "S1", "date": "20260126", "exception_type": 2},
            {"service_id": "S2", "date": "20260125", "exception_type": 1},
        ])
        s_map = build_service_calendar_map(cal_df, cal_dates_df)
        assert "WEEKDAY" in s_map["S1"], "Regular weekday schedule must not be purged by single holiday exception"
        assert "SATURDAY" in s_map["S1"]
        assert s_map["S2"] == {"SUNDAY"}, "Exception-based service S2 should only have SUNDAY added"

    def test_get_day_types_fallback(self):
        """Verifies missing service_id defaults to universal daily service."""
        assert get_day_types_for_service("MISSING_SERVICE", {}) == {"WEEKDAY", "SATURDAY", "SUNDAY"}

    def test_parse_gtfs_time_standard(self):
        """Verifies standard daytime timestamp parsing."""
        secs, h, time_str, rollover = parse_gtfs_time_to_seconds("08:30:15")
        assert secs == 8 * 3600 + 30 * 60 + 15
        assert h == 8
        assert time_str == "08:30:15"
        assert rollover is False

    def test_parse_gtfs_time_post_midnight_24h(self):
        """Verifies 24:15:00 rolls over to 00:15:00 and hour 0."""
        secs, h, time_str, rollover = parse_gtfs_time_to_seconds("24:15:00")
        assert secs == 87300
        assert h == 0
        assert time_str == "00:15:00"
        assert rollover is True

    def test_parse_gtfs_time_late_night_25h(self):
        """Verifies 25:30:45 rolls over to 01:30:45 and hour 1."""
        secs, h, time_str, rollover = parse_gtfs_time_to_seconds("25:30:45")
        assert secs == 25 * 3600 + 30 * 60 + 45
        assert h == 1
        assert time_str == "01:30:45"
        assert rollover is True

    def test_parse_gtfs_time_invalid_raises_error(self):
        """Verifies malformed time strings raise ValueError."""
        with pytest.raises(ValueError):
            parse_gtfs_time_to_seconds("invalid_time")
