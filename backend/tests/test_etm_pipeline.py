"""crowdwise/backend/tests/test_etm_pipeline.py
Unit and Integration tests for Milestone M2: Transit Data Pipeline & Demand Reconstruction (Features F06-F12).
Verifies:
- F06: Multi-format ETM data profiling, tri-modal sniffing (Mode A/B/C), validation, anomaly detection.
- F07: Mode A OD matrix accumulation, load recurrence, non-negativity, terminal clearance.
- F08: Mode B hybrid alighting inference engine (reverse-commute + gravity decay, alpha blend, terminal clearance).
- F09: Mode C Hare-Niemeyer largest remainder integer-conserving disaggregation.
- F10: Synthetic 28-day diurnal simulator, peak ratio validation, physical load conservation.
- F11: Data swap engine staging isolation, dry-run safety, and rollback safeguard.
- F12: DPDP Act 2023 compliance, HMAC-SHA-256 commuter pseudonymization, timestamp minute truncation, PII stripping.
"""
import io
import os
import sys
import tempfile
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
crowdwise_root = os.path.abspath(os.path.join(backend_dir, ".."))
scripts_dir = os.path.join(crowdwise_root, "scripts")

for p in [backend_dir, crowdwise_root, scripts_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.demand.exceptions import (
    ETMError,
    SchemaDetectionError,
    MandatoryColumnMissingError,
    CorruptDataFileError,
    EmptyStreamError,
    DataQualityThresholdExceeded,
)
from app.demand.types import QualityProfileResult, NormalizedTicketRecord, ZoneDemandRecord
from app.demand.anonymizer import TransitDataAnonymizer
from app.demand.profiler import ETMDataProfiler
from app.demand.alighting_model import ModeBAlightingInferenceEngine
from app.demand.reconstruction import ModeAReconstructor, ModeCDisaggregator, ZoneDemandAggregator
from app.models.transit import Base, DimStop, DimRoute, DimRoutePattern, RelPatternStop, DimTripStart
from app.models.demand import SysRuntimeMetadata, EtmStagingTicket, FactZoneDemand, FactZoneDemandStaging
from app.services.etm_service import (
    DemandReconstructionPipeline,
    profile_etm_stream,
    anonymize_ticket_record,
    hash_commuter_id,
    reconstruct_mode_a,
    reconstruct_mode_b,
    disaggregate_mode_c,
    aggregate_trip_zones,
)
from swap_data import run_data_swap, perform_rollback, ensure_metadata_tables


# ===========================================================================
# FIXTURES
# ===========================================================================

@pytest.fixture
def anonymizer():
    return TransitDataAnonymizer(salt="TEST_SECRET_SALT_2026")


@pytest.fixture
def profiler(anonymizer):
    return ETMDataProfiler(anonymizer=anonymizer)


@pytest.fixture
def synthetic_pattern_stops():
    """Returns a synthetic 10-stop route pattern: (stop_seq, stop_id, zone_id, cum_dist_km)."""
    return [
        (0, "STOP_001", 0, 0.0),
        (1, "STOP_002", 0, 1.2),
        (2, "STOP_003", 1, 2.5),
        (3, "STOP_004", 2, 4.0),
        (4, "STOP_005", 3, 5.8),
        (5, "STOP_006", 4, 7.3),
        (6, "STOP_007", 5, 8.9),
        (7, "STOP_008", 6, 10.5),
        (8, "STOP_009", 7, 12.0),
        (9, "STOP_010", 7, 13.5),
    ]


@pytest.fixture
def test_db_engine(synthetic_pattern_stops):
    """Creates a temporary in-memory SQLite database populated with minimal GTFS and demand tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    ensure_metadata_tables(engine)

    with Session(engine) as session:
        # Populate stops
        for seq, s_id, z_id, dist in synthetic_pattern_stops:
            session.add(DimStop(stop_id=s_id, stop_code=s_id, stop_name=f"Station {s_id}", stop_lat=28.6, stop_lon=77.2))
        
        # Populate route and pattern
        session.add(DimRoute(route_id="ROUTE_101", route_short_name="101UP", route_long_name="Route 101 UP", agency_id="DTC"))
        session.add(DimRoutePattern(pattern_id="PAT_101_0", route_id="ROUTE_101", direction_id=0, stop_count=10, total_dist_km=13.5, start_stop_id="STOP_001", end_stop_id="STOP_010"))
        session.add(DimRoutePattern(pattern_id="PAT_101_1", route_id="ROUTE_101", direction_id=1, stop_count=10, total_dist_km=13.5, start_stop_id="STOP_010", end_stop_id="STOP_001"))

        for seq, s_id, z_id, dist in synthetic_pattern_stops:
            session.add(RelPatternStop(pattern_id="PAT_101_0", stop_id=s_id, stop_sequence=seq, zone_id=z_id, cum_dist_km=dist))
            rev_seq = 9 - seq
            session.add(RelPatternStop(pattern_id="PAT_101_1", stop_id=s_id, stop_sequence=rev_seq, zone_id=z_id, cum_dist_km=13.5 - dist))

        session.commit()

    yield engine
    engine.dispose()


# ===========================================================================
# 1. FEATURE F12: DPDP ACT 2023 COMPLIANCE & COMMUTER PRIVACY
# ===========================================================================

class TestTransitDataAnonymizer:
    """Tests for TransitDataAnonymizer (F12)."""

    def test_hash_commuter_id_deterministic(self, anonymizer):
        """Same commuter ID and salt must always produce identical 64-char hex string."""
        h1 = anonymizer.hash_commuter_id("COMMUTER_12345")
        h2 = anonymizer.hash_commuter_id("COMMUTER_12345")
        assert h1 == h2
        assert len(h1) == 64
        assert all(c in "0123456789abcdef" for c in h1)

    def test_hash_commuter_id_salt_isolation(self):
        """Different salts must produce completely divergent pseudonyms."""
        a1 = TransitDataAnonymizer(salt="SALT_A")
        a2 = TransitDataAnonymizer(salt="SALT_B")
        h1 = a1.hash_commuter_id("COMMUTER_12345")
        h2 = a2.hash_commuter_id("COMMUTER_12345")
        assert h1 != h2

    def test_hash_empty_or_none(self, anonymizer):
        """None or empty string inputs return None."""
        assert anonymizer.hash_commuter_id(None) is None
        assert anonymizer.hash_commuter_id("") is None
        assert anonymizer.hash_commuter_id("   ") is None

    def test_truncate_timestamp_minute(self, anonymizer):
        """Seconds and microseconds must be truncated to 00."""
        dt = datetime(2026, 3, 15, 8, 42, 59, 123456)
        truncated = anonymizer.truncate_timestamp_minute(dt)
        assert truncated == datetime(2026, 3, 15, 8, 42, 0)

        # String input parsing
        s_truncated = anonymizer.truncate_timestamp_minute("2026-03-15T08:42:59Z")
        assert s_truncated == datetime(2026, 3, 15, 8, 42, 0)

    def test_sanitize_record_drops_pii(self, anonymizer):
        """Verifies commuter names, phone, email, Aadhaar, UPI, and financial fields are completely purged."""
        raw_record = {
            "ticket_id": "TCK_9999",
            "timestamp": "2026-03-15 08:30:45",
            "route_id": "101",
            "direction_id": 0,
            "boarding_stop_id": "STOP_001",
            "alighting_stop_id": "STOP_005",
            "fare_paid": 15.0,
            "passenger_count": 1,
            # PII fields to purge
            "passenger_name": "Rajesh Sharma",
            "phone": "+91-9876543210",
            "mobile": "9876543210",
            "email": "rajesh@example.com",
            "aadhaar_no": "1234-5678-9012",
            "upi_id": "rajesh@upi",
            "card_pan": "4111-XXXX-XXXX-1111",
            "cvv": "123",
            "smartcard_id": "CARD_887766",
        }
        sanitized = anonymizer.sanitize_record(raw_record)

        # Check PII fields are strictly removed
        for pii_field in ["passenger_name", "phone", "mobile", "email", "aadhaar_no", "upi_id", "card_pan", "cvv"]:
            assert pii_field not in sanitized

        # Check smartcard pseudonymization
        assert sanitized["smartcard_hash"] is not None
        assert len(sanitized["smartcard_hash"]) == 64
        assert sanitized["smartcard_hash"] != "CARD_887766"

        # Check timestamp truncation
        assert sanitized["timestamp"].second == 0
        assert sanitized["timestamp"].microsecond == 0

    def test_sanitize_dataframe(self, anonymizer):
        """Verifies bulk DataFrame sanitization."""
        df = pd.DataFrame([
            {"ticket_id": "T1", "timestamp": "2026-03-15 08:30:15", "smartcard_id": "SC1", "phone": "99999", "passenger_count": 1},
            {"ticket_id": "T2", "timestamp": "2026-03-15 08:35:45", "smartcard_id": "SC2", "passenger_name": "Alice", "passenger_count": 2},
        ])
        clean_df = anonymizer.sanitize_dataframe(df)
        assert "phone" not in clean_df.columns
        assert "passenger_name" not in clean_df.columns
        assert "smartcard_hash" in clean_df.columns
        assert len(clean_df["smartcard_hash"].iloc[0]) == 64


# ===========================================================================
# 2. FEATURE F06: MULTI-FORMAT PROFILING & TRI-MODAL SNIFFING
# ===========================================================================

class TestETMDataProfiler:
    """Tests for ETMDataProfiler (F06)."""

    def test_sniff_mode_a(self, profiler):
        """Data with boarding, alighting, and fare must be recognized as Mode A."""
        df = pd.DataFrame({
            "ticket_no": ["T1", "T2"],
            "timestamp": ["2026-03-15 08:00:00", "2026-03-15 08:05:00"],
            "route_id": ["101", "101"],
            "boarding_stop": ["STOP_001", "STOP_002"],
            "dest_stop": ["STOP_005", "STOP_006"],
            "amount": [15.0, 20.0],
            "passenger_count": [1, 1],
        })
        profile = profiler.profile_dataset(df)
        assert profile.mode == "mode_a"
        assert profile.has_alighting is True
        assert profile.quality_pass is True

    def test_sniff_mode_b(self, profiler):
        """Data with boarding and fare without alighting must be recognized as Mode B."""
        df = pd.DataFrame({
            "ticket_id": ["T1", "T2"],
            "date_time": ["2026-03-15 08:00:00", "2026-03-15 08:05:00"],
            "route": ["101", "101"],
            "source_stop": ["STOP_001", "STOP_002"],
            "fare": [10.0, 10.0],
            "passenger_count": [1, 1],
        })
        profile = profiler.profile_dataset(df)
        assert profile.mode == "mode_b"
        assert profile.has_alighting is False
        assert profile.quality_pass is True

    def test_sniff_mode_c(self, profiler):
        """Data with aggregated trip/route totals must be recognized as Mode C."""
        df = pd.DataFrame({
            "route_id": ["101", "101"],
            "date": ["2026-03-15", "2026-03-15"],
            "daily_boardings": [1200, 1350],
            "revenue": [12000.0, 13500.0],
        })
        profile = profiler.profile_dataset(df)
        assert profile.mode == "mode_c"
        assert profile.is_aggregated is True
        assert profile.quality_pass is True

    def test_reject_zero_byte_file(self, profiler):
        """0-byte file must be rejected with CorruptDataFileError or EmptyStreamError."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            tf_path = tf.name

        try:
            with pytest.raises((EmptyStreamError, CorruptDataFileError)):
                profiler.load_stream(tf_path)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_parquet_magic_bytes_validation(self, profiler):
        """Parquet file without PAR1 header must be rejected."""
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(b"NOT_PARQUET_DATA_STREAM")
            tf_path = tf.name

        try:
            with pytest.raises(CorruptDataFileError):
                profiler.load_stream(tf_path)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_reject_future_timestamps(self, profiler):
        """Timestamps in the far future (> 5 minutes ahead) must trigger quality warnings/failure."""
        far_future = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        df = pd.DataFrame({
            "ticket_id": ["T1"],
            "timestamp": [far_future],
            "route_id": ["101"],
            "from_stop_id": ["STOP_001"],
            "fare": [10.0],
            "passenger_count": [1],
        })
        profile = profiler.profile_dataset(df)
        assert profile.future_timestamp_count > 0

    def test_post_midnight_timestamp_normalization(self, profiler):
        """Hour 24+ notation (e.g. 24:15:00) must normalize to next-day 00:15:00."""
        df = pd.DataFrame({
            "ticket_id": ["T1"],
            "timestamp": ["2026-03-15 24:15:00"],
            "route_id": ["101"],
            "from_stop": ["STOP_001"],
            "fare": [10.0],
            "passenger_count": [1],
        })
        ingested = profiler.ingest_dataframe(df)
        parsed_dt = ingested["timestamp"].iloc[0]
        assert parsed_dt.day == 16
        assert parsed_dt.hour == 0
        assert parsed_dt.minute == 15

    def test_vendor_metadata_preservation(self, profiler):
        """Non-standard vendor columns (e.g. etm_serial, conductor_id) must be preserved in metadata dict."""
        df = pd.DataFrame({
            "ticket_id": ["T1"],
            "timestamp": ["2026-03-15 08:30:00"],
            "route_id": ["101"],
            "boarding_stop_id": ["STOP_001"],
            "fare_paid": [15.0],
            "passenger_count": [1],
            "etm_machine_serial": ["ETM_DELHI_042"],
            "conductor_badge": ["CD_9988"],
        })
        records = profiler.ingest_records(df)
        assert len(records) == 1
        meta = records[0].vendor_metadata
        assert meta["etm_machine_serial"] == "ETM_DELHI_042"
        assert meta["conductor_badge"] == "CD_9988"


# ===========================================================================
# 3. FEATURE F07: MODE A OD DEMAND RECONSTRUCTION
# ===========================================================================

class TestModeADemandReconstruction:
    """Tests for Mode A OD Matrix Reconstruction and Load Recurrence (F07)."""

    def test_od_matrix_and_load_recurrence(self, synthetic_pattern_stops):
        """Verifies OD accumulation and load recurrence L_s = L_{s-1} + B_s - A_s."""
        reconstructor = ModeAReconstructor()
        # 3 passengers:
        # P1: Stop 0 -> Stop 3
        # P2: Stop 1 -> Stop 5
        # P3: Stop 2 -> Stop 9
        tickets = [
            {"boarding_stop_id": "STOP_001", "alighting_stop_id": "STOP_004", "passenger_count": 1},
            {"boarding_stop_id": "STOP_002", "alighting_stop_id": "STOP_006", "passenger_count": 1},
            {"boarding_stop_id": "STOP_003", "alighting_stop_id": "STOP_010", "passenger_count": 1},
        ]

        res = reconstructor.reconstruct_trip(synthetic_pattern_stops, tickets)
        loads = res["loads"]
        boardings = res["boardings"]
        alightings = res["alightings"]
        N = len(synthetic_pattern_stops)

        # Expected boardings: stop 0: 1, stop 1: 1, stop 2: 1
        assert boardings[0] == 1
        assert boardings[1] == 1
        assert boardings[2] == 1
        # Expected alightings: stop 3: 1, stop 5: 1, stop 9: 1
        assert alightings[3] == 1
        assert alightings[5] == 1
        assert alightings[9] == 1

        # Check total boardings == total alightings
        assert sum(boardings) == sum(alightings) == 3

        # Check terminal clearance: L_{N-1} == 0
        assert loads[-1] == 0

        # Check non-negative loads at every stop
        for s in range(N):
            assert loads[s] >= 0

        # Check recurrence relation: L_s = L_{s-1} + B_s - A_s
        running_load = 0
        for s in range(N):
            running_load += boardings[s] - alightings[s]
            assert loads[s] == running_load

    def test_unmatched_stops_gracefully_ignored(self, synthetic_pattern_stops):
        """Tickets with non-existent stops must not crash the reconstructor."""
        reconstructor = ModeAReconstructor()
        tickets = [
            {"boarding_stop_id": "UNKNOWN_STOP", "alighting_stop_id": "STOP_005", "passenger_count": 1},
            {"boarding_stop_id": "STOP_001", "alighting_stop_id": "ANOTHER_UNKNOWN", "passenger_count": 1},
        ]
        res = reconstructor.reconstruct_trip(synthetic_pattern_stops, tickets)
        assert res["total_tickets"] == 2
        assert res["unmatched_tickets"] == 2


# ===========================================================================
# 4. FEATURE F08: MODE B ALIGHTING INFERENCE ENGINE
# ===========================================================================

class TestModeBAlightingInference:
    """Tests for Mode B Hybrid Alighting Inference Engine (F08)."""

    def test_penultimate_stop_certainty(self, synthetic_pattern_stops):
        """At stop N-2, the alighting probability for passengers to stop N-1 must be 1.0."""
        engine = ModeBAlightingInferenceEngine()
        N = len(synthetic_pattern_stops)
        probs = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=N - 2,
            reverse_boardings={},
        )
        assert probs[N - 1] == 1.0

    def test_terminal_clearance_and_conservation(self, synthetic_pattern_stops):
        """Terminal stop load must be 0, and total inferred alightings must equal total boardings."""
        engine = ModeBAlightingInferenceEngine()
        boardings_by_seq = {0: 15, 2: 10, 4: 8, 7: 5}
        total_b = sum(boardings_by_seq.values())

        res = engine.reconstruct_trip(
            pattern_stops=synthetic_pattern_stops,
            boardings_by_seq=boardings_by_seq,
            reverse_boardings={},
        )

        assert sum(res["alightings"]) == total_b
        assert res["loads"][-1] == 0
        for load in res["loads"]:
            assert load >= 0

    def test_gravity_distance_decay(self, synthetic_pattern_stops):
        """Alighting probability under distance decay must favor closer downstream stops over distant stops."""
        engine = ModeBAlightingInferenceEngine(decay_lambda=0.15)
        # Board at stop 0. Stops 1, 2, 3...
        probs = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=0,
            reverse_boardings={},
        )
        # Stop 1 is closer than Stop 5; P(1) should be > P(5) in pure decay (before final penultimate rule)
        assert probs[1] > probs[5]

    def test_zero_reverse_fallback_to_gravity(self, synthetic_pattern_stops):
        """When reverse boardings are absent or 0, alpha blend must be 0 (pure gravity decay)."""
        engine = ModeBAlightingInferenceEngine()
        probs_pure = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=0,
            reverse_boardings={},
        )
        probs_zero_dict = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=0,
            reverse_boardings={i: 0 for i in range(10)},
        )
        for s in range(1, 10):
            assert pytest.approx(probs_pure[s], rel=1e-5) == probs_zero_dict[s]

    def test_reverse_commute_alpha_blend(self, synthetic_pattern_stops):
        """When high reverse boardings exist, alpha > 0 and shifts probability towards high-reverse stops."""
        engine = ModeBAlightingInferenceEngine()
        # High reverse boardings at stop 8
        rev_boardings = {8: 100}
        probs_blend = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=0,
            reverse_boardings=rev_boardings,
        )
        probs_pure = engine.compute_alighting_probabilities(
            pattern_stops=synthetic_pattern_stops,
            boarding_idx=0,
            reverse_boardings={},
        )
        # Probability at stop 8 should be significantly boosted by reverse commute
        assert probs_blend[8] > probs_pure[8]


# ===========================================================================
# 5. FEATURE F09: MODE C DISAGGREGATION (HARE-NIEMEYER)
# ===========================================================================

class TestModeCDisaggregation:
    """Tests for Mode C Hare-Niemeyer Largest Remainder Disaggregation (F09)."""

    def test_hare_niemeyer_exact_sum_conservation(self):
        """Disaggregated integer passenger counts must sum EXACTLY to the target total."""
        disaggregator = ModeCDisaggregator()
        weights = [0.123, 0.456, 0.789, 0.055, 0.333]
        total_pax = 127
        assigned = disaggregator.disaggregate_hare_niemeyer(total_pax, weights)

        assert sum(assigned) == total_pax
        assert len(assigned) == len(weights)
        for count in assigned:
            assert isinstance(count, int)
            assert count >= 0

    def test_hare_niemeyer_zero_total(self):
        """Zero demand disaggregates into all zeros without error."""
        disaggregator = ModeCDisaggregator()
        weights = [0.5, 0.5]
        assigned = disaggregator.disaggregate_hare_niemeyer(0, weights)
        assert assigned == [0, 0]

    def test_disaggregate_daily_route_demand(self, synthetic_pattern_stops):
        """Verifies full Mode C disaggregation into scheduled trips and stops."""
        disaggregator = ModeCDisaggregator()
        # 3 scheduled trips with weights
        trip_profiles = [
            ("TRIP_01", 8, [1.0] * 10),
            ("TRIP_02", 12, [0.5] * 10),
            ("TRIP_03", 18, [1.2] * 10),
        ]
        daily_total = 450
        disagg_trips = disaggregator.disaggregate_daily_route_demand(
            daily_total_passengers=daily_total,
            scheduled_trip_profiles=trip_profiles,
        )

        assert len(disagg_trips) == 3
        total_assigned = sum(sum(trip["boardings"].values()) for trip in disagg_trips)
        assert total_assigned == daily_total


# ===========================================================================
# 6. 8-ZONE CORRIDOR AGGREGATION
# ===========================================================================

class TestZoneDemandAggregator:
    """Tests for 8-Zone Corridor Aggregation (F07/F09)."""

    def test_zone_partition_formula(self, synthetic_pattern_stops):
        """Verifies all stop indices map to zones 0-7 via floor(8*s / N)."""
        aggregator = ZoneDemandAggregator()
        N = len(synthetic_pattern_stops)
        for s in range(N):
            z = aggregator.get_zone_for_stop(s, N)
            assert 0 <= z <= 7

        # First stop must be in zone 0, last stop must be in zone 7
        assert aggregator.get_zone_for_stop(0, N) == 0
        assert aggregator.get_zone_for_stop(N - 1, N) == 7

    def test_trip_zone_aggregation_metrics(self, synthetic_pattern_stops):
        """Verifies zone-level mean_load, max_load, boardings, and alightings aggregation."""
        aggregator = ZoneDemandAggregator()
        loads = [10, 15, 20, 25, 20, 15, 10, 5, 2, 0]
        boardings = [10, 5, 5, 5, 0, 0, 0, 0, 0, 0]
        alightings = [0, 0, 0, 0, 5, 5, 5, 5, 3, 2]

        zones = aggregator.aggregate_trip_zones(
            trip_id="TRIP_DEMO",
            route_id="ROUTE_101",
            direction_id=0,
            day_type="weekday",
            trip_date="2026-03-15",
            hour=8,
            pattern_stops=synthetic_pattern_stops,
            loads=loads,
            boardings=boardings,
            alightings=alightings,
        )

        assert len(zones) > 0
        for z in zones:
            assert z["route_id"] == "ROUTE_101"
            assert z["direction_id"] == 0
            assert 0 <= z["zone_id"] <= 7
            assert z["max_load"] >= z["mean_load"]
            assert z["boardings_total"] >= 0
            assert z["alightings_total"] >= 0


# ===========================================================================
# 7. FEATURE F10: SYNTHETIC DATA GENERATOR & DIURNAL CURVE
# ===========================================================================

class TestSyntheticSimulatorArtifacts:
    """Tests for Synthetic Data Generator outputs (F10)."""

    def test_synthetic_parquet_files_exist(self):
        """Verifies generated synthetic Parquet datasets exist and are non-empty."""
        synth_dir = os.path.join(crowdwise_root, "data", "synthetic")
        demo_tickets_path = os.path.join(synth_dir, "demo_tickets.parquet")
        truth_loads_path = os.path.join(synth_dir, "truth_loads_demo.parquet")

        assert os.path.exists(demo_tickets_path), f"Missing {demo_tickets_path}"
        assert os.path.exists(truth_loads_path), f"Missing {truth_loads_path}"

        df_tickets = pd.read_parquet(demo_tickets_path)
        df_loads = pd.read_parquet(truth_loads_path)

        assert len(df_tickets) > 100_000
        assert len(df_loads) > 20_000

        # Required ticket columns
        expected_cols = ["ticket_id", "timestamp", "route_id", "direction_id", "boarding_stop_id"]
        for c in expected_cols:
            assert c in df_tickets.columns
        assert "fare" in df_tickets.columns or "fare_paid" in df_tickets.columns

    def test_synthetic_diurnal_curve_peak_ratios(self):
        """Verifies morning peak (8-10am) ratio >= 1.25 and evening peak (17-20pm) ratio >= 1.20 over midday."""
        truth_loads_path = os.path.join(crowdwise_root, "data", "synthetic", "truth_loads_demo.parquet")
        df_loads = pd.read_parquet(truth_loads_path)

        hourly = df_loads.groupby("hour")["mean_load"].mean()
        morning_peak = hourly.loc[8:10].mean()
        midday = hourly.loc[12:14].mean()
        evening_peak = hourly.loc[17:20].mean()

        m_ratio = morning_peak / midday
        e_ratio = evening_peak / midday

        assert m_ratio >= 1.25, f"Morning peak ratio {m_ratio:.2f} < 1.25"
        assert e_ratio >= 1.20, f"Evening peak ratio {e_ratio:.2f} < 1.20"


# ===========================================================================
# 8. FEATURE F11: DATA SWAP ENGINE & ROLLBACK SAFEGUARD
# ===========================================================================

class TestDataSwapEngine:
    """Tests for Data Swap CLI & Atomic Staging Operations (F11)."""

    def test_dry_run_preserves_runtime_metadata(self, test_db_engine):
        """Dry-run must validate all 9 steps without modifying production metadata."""
        db_url = str(test_db_engine.url)

        # Create a small valid test parquet
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf_path = tf.name

        df_test = pd.DataFrame([
            {
                "ticket_id": f"T_{i}",
                "timestamp": "2026-03-15 08:30:00",
                "route_id": "ROUTE_101",
                "direction_id": 0,
                "boarding_stop_id": "STOP_001",
                "fare_paid": 10.0,
                "passenger_count": 1,
            }
            for i in range(20)
        ])
        df_test.to_parquet(tf_path, index=False)

        try:
            res = run_data_swap(source_path=tf_path, format_mode="mode_b", dry_run=True, db_url=db_url)
            assert res["status"] == "dry_run_success"

            # Verify production metadata was NOT changed
            with Session(test_db_engine) as session:
                meta = session.get(SysRuntimeMetadata, "active_tier")
                assert meta.value == "demo_synthetic"
                mode = session.get(SysRuntimeMetadata, "data_mode")
                assert mode.value == "demo"
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_rollback_restores_demo_state(self, test_db_engine):
        """Rollback safeguard must set data_mode=demo and active_tier=demo_synthetic."""
        # Set metadata to organizer mode
        with Session(test_db_engine) as session:
            session.merge(SysRuntimeMetadata(key="active_tier", value="organizer_production"))
            session.merge(SysRuntimeMetadata(key="data_mode", value="live"))
            session.commit()

        # Execute rollback
        perform_rollback(test_db_engine)

        with Session(test_db_engine) as session:
            meta = session.get(SysRuntimeMetadata, "active_tier")
            assert meta.value == "demo_synthetic"
            mode = session.get(SysRuntimeMetadata, "data_mode")
            assert mode.value == "demo"


# ===========================================================================
# 9. INTEGRATION: FULL ETM SERVICE FACADE
# ===========================================================================

class TestETMServiceIntegration:
    """End-to-end integration tests using ETM Service facade functions."""

    def test_facade_service_mode_b_reconstruction(self, test_db_engine):
        """Tests the unified DemandReconstructionPipeline on test database."""
        pipeline = DemandReconstructionPipeline(db_url_or_engine=test_db_engine)

        raw_df = pd.DataFrame([
            {
                "ticket_id": f"T_{i}",
                "timestamp": "2026-03-15 08:15:00",
                "route_id": "ROUTE_101",
                "direction_id": 0,
                "boarding_stop_id": f"STOP_00{1 + (i % 5)}",
                "fare_paid": 15.0,
                "passenger_count": 1,
            }
            for i in range(50)
        ])

        trip_zones, hourly_df = pipeline.process_ticket_stream(raw_df, mode="mode_b")
        assert len(trip_zones) > 0
        assert not hourly_df.empty
        assert "mean_load" in hourly_df.columns
        assert "max_load" in hourly_df.columns
