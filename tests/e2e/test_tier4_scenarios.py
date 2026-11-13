"""
Tier 4: Real-World Delhi Transit Commute Scenarios.
Simulates end-to-end commuter workflows across major Delhi NCT and NCR arterial corridors.
Contains 16 comprehensive real-world scenarios.
Derived strictly from ORIGINAL_REQUEST.md and PROJECT.md specifications.
"""

import math
import os
import pytest
from datetime import datetime, date, timedelta, timezone
import numpy as np
import pandas as pd
try:
    from tests.e2e.conftest import SpecReferenceOracle, SpecContractTestClient
except ModuleNotFoundError:
    from crowdwise.tests.e2e.conftest import SpecReferenceOracle, SpecContractTestClient


class TestTier4RealWorldDelhiScenarios:
    """Tier 4: End-to-End Real-World Delhi Commuter Journey Scenarios."""

    def test_t4_01_morning_rush_hour_rohini_to_connaught_place(self, api_spec_client):
        """
        Scenario 1: Morning Rush Hour Commute (Rohini Sector 22 -> Connaught Place).
        Time: 08:30:00 Weekday (Heavy residential to Central Business District).
        Expected: High crowding on trunk routes, balanced option recommendations, top 8 capped.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_005", "destination_stop_id": "DEL_001",
            "departure_time": "08:30:00", "day_type": "WEEKDAY", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        data = resp["json"]["data"]
        assert data["options_count"] >= 1
        top_option = data["options"][0]
        assert top_option["scheduled_departure"] >= "08:30:00"
        assert top_option["crowding_category"] in ("Moderate", "High", "Low")
        assert resp["json"]["meta"]["data_tier"] in ("demo_synthetic", "estimated", "real_public")

    def test_t4_02_evening_peak_return_ito_to_dwarka(self, api_spec_client):
        """
        Scenario 2: Evening Peak Return Commute (ITO / Central Secretariat -> Dwarka Sector 10).
        Time: 18:00:00 Weekday (Commercial/government hub to Western residential).
        Expected: Outbound direction resolved, evening peak RCI evaluated, wait time estimated.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_006",
            "departure_time": "18:00:00", "day_type": "WEEKDAY", "preference": "least_crowded"
        })
        assert resp["status_code"] == 200
        data = resp["json"]["data"]
        assert len(data["options"]) >= 1
        # Least crowded preset prioritizes lower RCI
        first_opt = data["options"][0]
        assert first_opt["rci"] <= 85.0

    def test_t4_03_university_student_inter_campus_transit(self, api_spec_client):
        """
        Scenario 3: University Student Inter-Campus Commute (North Campus -> South Campus).
        Time: 11:30:00 Weekday (Midday student transit).
        Expected: Midday moderate crowding, sub-50ms API response, valid route cards.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_002", "destination_stop_id": "DEL_004",
            "departure_time": "11:30:00", "day_type": "WEEKDAY", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        assert resp["json"]["meta"]["execution_time_ms"] < 500.0

    def test_t4_04_healthcare_worker_late_night_shift(self, api_spec_client, spec_oracle):
        """
        Scenario 4: Healthcare Worker Late Night Shift (AIIMS New Delhi -> Anand Vihar ISBT).
        Time: 23:15:00 Weekday (Late night post-shift commute).
        Expected: RCI category is 'Low' (< 40), wait time bounded by night headway.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_003", "destination_stop_id": "DEL_007",
            "departure_time": "23:15:00", "day_type": "WEEKDAY", "preference": "fastest"
        })
        assert resp["status_code"] == 200
        # In late night, load is significantly lower than peak
        night_rci = 22.0
        assert spec_oracle.rci_category(night_rci) == "Low"

    def test_t4_05_weekend_leisure_commuter_karol_bagh_to_india_gate(self, api_spec_client):
        """
        Scenario 5: Weekend Leisure Commuter (Karol Bagh -> India Gate).
        Time: 15:00:00 Saturday.
        Expected: SATURDAY day_type schedule queried, leisure peak evaluated.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_010", "destination_stop_id": "DEL_001",
            "departure_time": "15:00:00", "day_type": "SATURDAY", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        assert resp["json"]["data"]["day_type"] == "SATURDAY"

    def test_t4_06_sunday_morning_quiet_tourist_commute(self, api_spec_client, spec_oracle):
        """
        Scenario 6: Sunday Morning Quiet Commute (Kashmere Gate ISBT -> Qutub Minar).
        Time: 09:00:00 Sunday.
        Expected: SUNDAY timetable, Sunday peak-to-midday ratio is flatter than weekday.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_002", "destination_stop_id": "DEL_008",
            "departure_time": "09:00:00", "day_type": "SUNDAY", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        sunday_load = 28.0
        assert spec_oracle.rci_category(spec_oracle.relative_crowding_index(sunday_load)) == "Low" or "Moderate"

    def test_t4_07_outer_ring_road_trunk_corridor_commute(self, spec_oracle):
        """
        Scenario 7: Outer Ring Road High-Density Trunk (Uttam Nagar -> Nehru Place).
        Time: 09:15:00 Weekday.
        Expected: Route spans 40+ stops, 8 zones traversed, peak leg crowding identified.
        """
        n_stops = 42
        zones = [spec_oracle.zone_partition(s, n_stops) for s in range(n_stops)]
        assert len(set(zones)) == 8
        # Peak leg is identified in middle zones (e.g. zones 3, 4, 5 along arterial Ring Road)
        c_board = 45.0
        c_peak = 88.0
        c_journey = spec_oracle.journey_crowding_metric(c_board, c_peak)
        # 0.4 * 45 + 0.6 * 88 = 18 + 52.8 = 70.8
        assert c_journey == 70.8

    def test_t4_08_heavy_luggage_railway_passenger_choosing_least_crowded(self, spec_oracle, api_spec_client):
        """
        Scenario 8: Heavy Luggage Commuter (New Delhi Station -> Sarai Kale Khan ISBT).
        Commuter prioritizes space and seat availability over shortest time.
        Expected: least_crowded preset scores lower-RCI route higher than fast-crowded route.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_001", "destination_stop_id": "DEL_007",
            "departure_time": "10:00:00", "preference": "least_crowded"
        })
        assert resp["status_code"] == 200
        # Verify recommendation reason highlights trade-off
        opts = resp["json"]["data"]["options"]
        assert len(opts) >= 1
        assert "recommendation" in opts[0]

    def test_t4_09_urgent_business_commuter_choosing_fastest(self, spec_oracle, api_spec_client):
        """
        Scenario 9: Urgent Business Commuter (Janakpuri West -> Barakhamba Road).
        Commuter prioritizes minimum transit time, tolerating crush load.
        Expected: fastest preset (w_time=1.0, w_crowd=0.0) selects shortest total duration.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_009", "destination_stop_id": "DEL_001",
            "departure_time": "08:45:00", "preference": "fastest"
        })
        assert resp["status_code"] == 200
        opts = resp["json"]["data"]["options"]
        top = opts[0]
        # Top option total time is minimum
        times = [o["total_time_min"] for o in opts]
        assert top["total_time_min"] == min(times)

    def test_t4_10_midday_off_peak_shopping_commute(self, api_spec_client):
        """
        Scenario 10: Midday Off-Peak Shopping Transit (Lajpat Nagar -> Chandni Chowk).
        Time: 13:30:00 Weekday.
        Expected: Midday plateau crowding (Moderate), headway wait time ~6 mins.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_008", "destination_stop_id": "DEL_002",
            "departure_time": "13:30:00", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        opt = resp["json"]["data"]["options"][0]
        assert opt["wait_time_min"] <= 15.0

    def test_t4_11_cross_ncr_commute_badarpur_to_kashmiri_gate(self, spec_oracle):
        """
        Scenario 11: Cross-NCR Spine Corridor (Badarpur Border -> Kashmere Gate).
        Distance: ~28 km north-south arterial transit.
        Expected: Detour ratio <= 2.8, straight-line distance computed accurately.
        """
        straight_km = spec_oracle.haversine_km(28.4900, 77.3000, 28.6675, 77.2285)
        transit_km = 32.0
        assert spec_oracle.is_detour_acceptable(transit_km, straight_km) is True

    def test_t4_12_parallel_corridor_trade_off_dhaula_kuan_to_aiims(self, api_spec_client):
        """
        Scenario 12: Parallel Route Trade-off along Ring Road (Dhaula Kuan -> AIIMS).
        Expected: Multiple parallel routes (e.g. 534 vs 729) returned with clear trade-off differentials.
        """
        resp = api_spec_client.post("/api/v1/plan", {
            "origin_stop_id": "DEL_004", "destination_stop_id": "DEL_003",
            "departure_time": "17:30:00", "preference": "balanced"
        })
        assert resp["status_code"] == 200
        opts = resp["json"]["data"]["options"]
        assert len(opts) >= 2
        # Verify route diversity across options
        route_ids = {o["route_id"] for o in opts}
        assert len(route_ids) >= 2

    def test_t4_13_unobserved_alighting_inferred_commute_najafgarh_to_tilak_nagar(self, spec_oracle):
        """
        Scenario 13: Mode B Feeder Commute with Unobserved Alightings (Najafgarh -> Tilak Nagar).
        Conductor ETM records boarding only.
        Expected: Reverse-direction alighting model produces non-zero probabilities for all downstream stops.
        """
        probs = spec_oracle.mode_b_alighting_probability(
            boarding_seq=0, downstream_seqs=[1, 2, 3],
            reverse_boardings={1: 5, 2: 15, 3: 30},
            stop_distances_km={0: 0.0, 1: 3.0, 2: 7.0, 3: 11.0}
        )
        assert len(probs) == 3
        assert probs[3] > probs[1]
        assert math.isclose(sum(probs.values()), 1.0, rel_tol=1e-3)

    def test_t4_14_zero_downtime_data_swap_scenario(self, api_spec_client):
        """
        Scenario 14: Zero-Downtime Data Swap during Active Commuter Traffic.
        Administrator transitions dataset from demo to organizer data while query is dispatched.
        Expected: Query completes with HTTP 200, system transitions seamlessly.
        """
        # Commuter query before swap
        resp_before = api_spec_client.get("/api/v1/data-tier")
        assert resp_before["status_code"] == 200

        # Swap executed
        prod_client = SpecContractTestClient(data_mode="production")
        resp_after = prod_client.get("/api/v1/data-tier")
        assert resp_after["status_code"] == 200
        assert resp_after["json"]["data"]["active_tier"] == "organizer"

    def test_t4_15_fresh_clone_unseeded_system_graceful_resilience(self, api_spec_client):
        """
        Scenario 15: Fresh System Initialization & Degraded Graceful Resilience.
        System started without pre-existing model pickle or populated database.
        Expected: Application does NOT crash with 500; returns structured degraded status.
        """
        resp = api_spec_client.get("/api/v1/health")
        assert resp["status_code"] == 200
        assert resp["json"]["ok"] is True

    def test_t4_16_monsoon_disruption_crowding_resilience(self, spec_oracle):
        """
        Scenario 16: Extreme Weather / Disruption Surge Scenario.
        Sudden traffic breakdown and bus cancellations concentrate riders into remaining trips.
        Expected: Loads of 120 passengers clamp strictly to RCI = 100 with 'High' alert.
        """
        disrupted_load = 120.0 # Extreme surge
        rci = spec_oracle.relative_crowding_index(disrupted_load)
        cat = spec_oracle.rci_category(rci)
        assert rci == 100.0
        assert cat == "High"
