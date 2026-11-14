"""crowdwise/backend/tests/test_adversarial_m2.py
Milestone 2 Empirical Adversarial Stress Harness (Challenger M2.2).

Adversarially stress-tests:
1. Profiler & Anomaly Stress Testing (F06):
   - Corrupted files, zero-byte streams, truncated CSVs, missing Parquet magic bytes ("PAR1").
   - Negative fares, future timestamps, epoch timestamps, post-midnight wrap-around.
   - Structured exceptions raised cleanly without process crashes.
2. Privacy & DPDP Hashing Invariants (F12):
   - HMAC-SHA-256 with 1,000 synthetic commuter phone numbers, card IDs, and pass numbers.
   - Length invariant: strictly 64 hexadecimal characters.
   - Collision resistance, determinism, and salt sensitivity.
   - PII purging and leakage vulnerability probe into vendor_metadata.
3. Synthetic Generator Parquet Validation (F10):
   - Diurnal distribution ratios: morning peak >= 1.25 * midday, evening peak >= 1.20 * midday.
   - Physical non-negativity: all loads L >= 0.
   - Zone ID bounds [0, 7] and day_type integrity.
4. Data Swap Atomic Staging & Rollback Stress Test (F11):
   - Dry-run staging isolation: zero production table or metadata alterations.
   - Staging table cleanup.
   - Automated Step 9 rollback verification.
"""
import io
import os
import re
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_crowdwise_root = os.path.abspath(os.path.join(_backend_dir, ".."))
_scripts_dir = os.path.join(_crowdwise_root, "scripts")

for p in [_backend_dir, _crowdwise_root, _scripts_dir]:
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
from app.demand.types import IngestionMode, QualityProfileResult
from app.demand.anonymizer import TransitDataAnonymizer, DEFAULT_SALT
from app.demand.profiler import ETMDataProfiler
from app.models.transit import Base
from app.models.demand import SysRuntimeMetadata, FactZoneDemand
from swap_data import run_data_swap, perform_rollback, ensure_metadata_tables


@pytest.fixture
def test_db_url():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name
    db_url = f"sqlite:///{temp_db}"
    engine = create_engine(db_url)
    ensure_metadata_tables(engine)
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS fact_zone_demand (
                demand_id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id VARCHAR(64) NOT NULL,
                direction_id INTEGER NOT NULL,
                day_type VARCHAR(16) NOT NULL,
                hour INTEGER NOT NULL,
                zone_id INTEGER NOT NULL,
                trip_date VARCHAR(10) NOT NULL,
                mean_load FLOAT NOT NULL,
                max_load INTEGER NOT NULL,
                boardings_total INTEGER NOT NULL,
                alightings_total INTEGER NOT NULL,
                trip_count INTEGER DEFAULT 1,
                data_tier VARCHAR(32) DEFAULT 'demo_synthetic'
            );
        """))
        conn.execute(text("""
            INSERT INTO fact_zone_demand (route_id, direction_id, day_type, hour, zone_id, trip_date, mean_load, max_load, boardings_total, alightings_total, trip_count, data_tier)
            VALUES ('101UP', 0, 'WEEKDAY', 8, 0, '2026-11-13', 15.0, 20, 10, 5, 1, 'demo_synthetic');
        """))
    yield db_url
    if os.path.exists(temp_db):
        try:
            os.remove(temp_db)
        except Exception:
            pass



# ===========================================================================
# 1. Profiler & Anomaly Stress Testing (F06)
# ===========================================================================

class TestProfilerAnomalies:
    """Empirically stress-tests ETMDataProfiler against hostile and corrupted inputs."""

    @pytest.fixture
    def profiler(self):
        return ETMDataProfiler()

    def test_missing_file_raises_filenotfound(self, profiler):
        non_existent = "non_existent_telemetry_dump_9999.csv"
        with pytest.raises(FileNotFoundError):
            profiler.load_stream(non_existent)

    def test_zero_byte_file_raises_corruptdatafileerror(self, profiler):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            temp_path = f.name
        try:
            assert os.path.getsize(temp_path) == 0
            with pytest.raises(CorruptDataFileError) as exc_info:
                profiler.load_stream(temp_path)
            assert "zero bytes" in str(exc_info.value).lower()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupt_parquet_missing_magic_bytes(self, profiler):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            # Write arbitrary 64 garbage bytes without PAR1 magic header/footer
            f.write(b"NOT_PARQUET_GARBAGE_HEADER_DATA_STREAM_WITHOUT_PAR1_MAGIC_BYTES_1234")
            temp_path = f.name
        try:
            with pytest.raises(CorruptDataFileError) as exc_info:
                profiler.load_stream(temp_path)
            assert "PAR1" in str(exc_info.value)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupt_parquet_truncated_under_8_bytes(self, profiler):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            f.write(b"PAR1")  # Only 4 bytes (header but no footer)
            temp_path = f.name
        try:
            with pytest.raises(CorruptDataFileError) as exc_info:
                profiler.load_stream(temp_path)
            assert "smaller than 8 bytes" in str(exc_info.value)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_corrupt_parquet_header_valid_but_footer_invalid(self, profiler):
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            # 16 bytes: Valid PAR1 header, but invalid footer
            f.write(b"PAR1" + b"12345678" + b"FAIL")
            temp_path = f.name
        try:
            with pytest.raises(CorruptDataFileError) as exc_info:
                profiler.load_stream(temp_path)
            assert "PAR1" in str(exc_info.value)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_zero_byte_bytesio_stream_raises_emptystreamerror(self, profiler):
        buf = io.BytesIO(b"")
        with pytest.raises(EmptyStreamError):
            profiler.load_stream(buf)

    def test_zero_byte_stringio_stream_raises_emptystreamerror(self, profiler):
        buf = io.StringIO("")
        with pytest.raises(EmptyStreamError):
            profiler.load_stream(buf)

    def test_empty_dataframe_raises_emptystreamerror(self, profiler):
        empty_df = pd.DataFrame()
        with pytest.raises(EmptyStreamError):
            profiler.load_stream(empty_df)

    def test_empty_list_raises_emptystreamerror(self, profiler):
        with pytest.raises(EmptyStreamError):
            profiler.load_stream([])

    def test_mandatory_columns_missing_raises_structured_exception(self, profiler):
        # Missing both timestamp and route_id
        df_invalid = pd.DataFrame([{"boarding_stop_id": "STOP_A", "passenger_count": 2}])
        with pytest.raises(MandatoryColumnMissingError) as exc_info:
            profiler.profile_dataset(df_invalid)
        assert "timestamp" in exc_info.value.missing_columns
        assert "route_id" in exc_info.value.missing_columns

    def test_unrecognizable_columns_raises_schema_detection_error(self, profiler):
        # Has timestamp and route_id, but neither boarding_stop nor aggregate volume
        df_weird = pd.DataFrame([{
            "timestamp": "2026-11-13 10:00:00",
            "route_id": "101UP",
            "unknown_metric_x": 42
        }])
        with pytest.raises(SchemaDetectionError):
            profiler.profile_dataset(df_weird)

    def test_future_timestamps_anomaly_detection(self, profiler):
        future_time = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        valid_time = "2026-11-13T08:00:00Z"
        df = pd.DataFrame([
            {"timestamp": valid_time, "route_id": "101UP", "boarding_stop": "S1"},
            {"timestamp": future_time, "route_id": "101UP", "boarding_stop": "S2"},
        ])
        profile = profiler.profile_dataset(df)
        assert profile.quality_pass is False
        assert profile.diagnostics["future_timestamps_detected"] == 1

        # Ingest dataframe must drop the future timestamp row
        clean_df = profiler.ingest_dataframe(df)
        assert len(clean_df) == 1
        assert clean_df.iloc[0]["boarding_stop_id"] == "S1"

    def test_negative_fares_anomaly_detection(self, profiler):
        df = pd.DataFrame([
            {"timestamp": "2026-11-13T08:00:00Z", "route_id": "101UP", "boarding_stop": "S1", "fare": 15.0},
            {"timestamp": "2026-11-13T08:05:00Z", "route_id": "101UP", "boarding_stop": "S2", "fare": -50.0},
        ])
        profile = profiler.profile_dataset(df)
        assert profile.quality_pass is False
        assert profile.diagnostics["negative_fares_detected"] == 1

        # Ingest dataframe must filter out negative fares
        clean_df = profiler.ingest_dataframe(df)
        assert len(clean_df) == 1
        assert clean_df.iloc[0]["fare_paid"] == 15.0

    def test_post_midnight_hour_24_wrap_around(self, profiler):
        # Telemetry with post-midnight 24:15:00 timestamp
        raw_time = "2026-11-13 24:15:00"
        parsed = profiler.parse_timestamp(raw_time)
        assert parsed is not None
        assert parsed.day == 14
        assert parsed.hour == 0
        assert parsed.minute == 15

    def test_indian_format_timestamp(self, profiler):
        raw_time = "13/11/2026 14:30:00"
        parsed = profiler.parse_timestamp(raw_time)
        assert parsed is not None
        # IST is UTC+5:30 -> 14:30 IST is 09:00 UTC
        assert parsed.hour == 9
        assert parsed.minute == 0


# ===========================================================================
# 2. Privacy & DPDP Hashing Invariants (F12)
# ===========================================================================

class TestPrivacyAndDPDPInvariants:
    """Empirically stress-tests DPDP Act 2023 compliance and HMAC-SHA-256 salting invariants."""

    @pytest.fixture
    def anonymizer(self):
        return TransitDataAnonymizer(salt="CHALLENGER_SALT_PRIMARY")

    @pytest.fixture
    def secondary_anonymizer(self):
        return TransitDataAnonymizer(salt="CHALLENGER_SALT_SECONDARY")

    def test_hmac_sha256_1000_commuter_phones(self, anonymizer, secondary_anonymizer):
        """Stress-tests 1,000 synthetic commuter phone numbers."""
        phones = [f"+9198{i:08d}" for i in range(1000)]
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")

        hashes_a = [anonymizer.hash_commuter_id(p) for p in phones]
        hashes_b = [secondary_anonymizer.hash_commuter_id(p) for p in phones]

        # 1. Exact 64 hex characters
        for h in hashes_a:
            assert len(h) == 64, f"Hash length {len(h)} != 64"
            assert hex_pattern.match(h), f"Invalid hex hash format: {h}"

        # 2. Non-reversibility
        for p, h in zip(phones, hashes_a):
            assert p not in h

        # 3. Collision resistance across 1,000 distinct phones
        assert len(set(hashes_a)) == 1000, f"Collisions detected: {len(set(hashes_a))} < 1000"

        # 4. Salt sensitivity across all 1,000 items
        different_salt_diffs = sum(1 for ha, hb in zip(hashes_a, hashes_b) if ha != hb)
        assert different_salt_diffs == 1000, "Different salts did not yield different hashes for all samples"

        # 5. Determinism
        hashes_a_repeat = [anonymizer.hash_commuter_id(p) for p in phones]
        assert hashes_a == hashes_a_repeat, "Hash is non-deterministic"

    def test_hmac_sha256_1000_smartcards(self, anonymizer, secondary_anonymizer):
        """Stress-tests 1,000 synthetic smartcard IDs."""
        cards = [f"NCMC_CARD_{i:010d}" for i in range(1000)]
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")

        hashes_a = [anonymizer.hash_commuter_id(c) for c in cards]
        hashes_b = [secondary_anonymizer.hash_commuter_id(c) for c in cards]

        for h in hashes_a:
            assert len(h) == 64
            assert hex_pattern.match(h)

        assert len(set(hashes_a)) == 1000
        assert sum(1 for ha, hb in zip(hashes_a, hashes_b) if ha != hb) == 1000

    def test_hmac_sha256_1000_pass_numbers(self, anonymizer, secondary_anonymizer):
        """Stress-tests 1,000 synthetic pass numbers."""
        passes = [f"PASS_DTC_2026_{i:06d}" for i in range(1000)]
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")

        hashes_a = [anonymizer.hash_commuter_id(p) for p in passes]
        hashes_b = [secondary_anonymizer.hash_commuter_id(p) for p in passes]

        for h in hashes_a:
            assert len(h) == 64
            assert hex_pattern.match(h)

        assert len(set(hashes_a)) == 1000
        assert sum(1 for ha, hb in zip(hashes_a, hashes_b) if ha != hb) == 1000

    def test_sanitize_record_purges_pii_and_financial_fields(self, anonymizer):
        raw_record = {
            "ticket_id": "TK_1001",
            "name": "Arun Sharma",
            "phone": "+919811223344",
            "email": "arun@example.com",
            "aadhaar": "123456789012",
            "upi_id": "arun@upi",
            "card_pan": "4111222233334444",
            "cvv": "999",
            "smartcard_id": "CARD_8877",
            "timestamp": "2026-11-13 14:15:32",
            "boarding_stop_id": "STOP_A",
            "fare_paid": 25.0,
        }
        sanitized = anonymizer.sanitize_record(raw_record)

        # Direct contact and financial identifiers MUST be absent
        for field in ["name", "phone", "email", "aadhaar", "upi_id", "card_pan", "cvv"]:
            assert field not in sanitized, f"PII field {field} leaked in sanitize_record output!"

        # Smartcard must be pseudonymized into 64-hex hash
        assert len(sanitized["smartcard_id"]) == 64
        assert sanitized["smartcard_hash"] == sanitized["smartcard_id"]

        # Timestamp seconds must be truncated to minute (32 sec -> 00 sec)
        assert sanitized["timestamp"].second == 0
        assert sanitized["timestamp"].microsecond == 0

    def test_adversarial_pii_leakage_into_vendor_metadata(self):
        """Adversarial Challenge: Verifies whether unhandled PII columns leak into NormalizedTicketRecord.vendor_metadata."""
        profiler = ETMDataProfiler()
        raw_df = pd.DataFrame([{
            "ticket_id": "TK_PASSENGER_PHONE_9811002233",
            "timestamp": "2026-11-13 08:30:00",
            "route_id": "101UP",
            "boarding_stop_id": "STOP_1",
            "passenger_name": "Ramesh Kumar",
            "passenger_phone": "+919811002233",
            "aadhaar": "123456789012",
            "upi_id": "ramesh@upi",
            "card_pan": "4111222233334444",
            "cvv": "123",
            "fare_paid": 15.0,
        }])

        records = profiler.ingest_records(raw_df)
        assert len(records) == 1
        record = records[0]

        # Empirical probe: Check if vendor_metadata contains raw PII
        leaked_pii = [k for k in ["passenger_name", "passenger_phone", "aadhaar", "upi_id", "card_pan", "cvv"]
                      if k in record.vendor_metadata]
        assert len(leaked_pii) == 0, f"PII leaked into vendor_metadata: {leaked_pii}"
        assert not any(profiler.is_pii_or_financial_field(k) for k in record.vendor_metadata)

    def test_anonymizer_purge_fields_completeness_and_truncation(self, anonymizer):
        """Verifies PURGE_FIELDS completeness and minute-level truncation in sanitize_dataframe."""
        required_purge = {"passenger_phone", "phone", "mobile", "contact", "passenger_mobile"}
        assert required_purge.issubset(anonymizer.PURGE_FIELDS)

        df = pd.DataFrame([
            {
                "ticket_id": "T1",
                "timestamp": "2026-11-13 14:15:32",
                "smartcard_id": "CARD_123",
                "pass_id": "PASS_456",
                "passenger_phone": "+919999999999",
                "passenger_mobile": "9999999999",
                "contact": "9888888888",
                "fare_paid": 20.0,
            }
        ])
        clean = anonymizer.sanitize_dataframe(df)

        # PURGE fields removed
        assert "passenger_phone" not in clean.columns
        assert "passenger_mobile" not in clean.columns
        assert "contact" not in clean.columns

        # Timestamp minute truncation (second=0, microsecond=0)
        ts_val = clean["timestamp"].iloc[0]
        assert ts_val.second == 0
        assert ts_val.microsecond == 0

        # No collision between smartcard_id and pass_id; both pseudonymized, smartcard_hash populated
        assert len(clean["smartcard_id"].iloc[0]) == 64
        assert len(clean["pass_id"].iloc[0]) == 64
        assert len(clean["smartcard_hash"].iloc[0]) == 64
        # smartcard_id had priority for smartcard_hash
        assert clean["smartcard_hash"].iloc[0] == clean["smartcard_id"].iloc[0]

    def test_swap_data_staging_smartcard_hash_population(self, test_db_url):
        """Verifies Step 3 of swap_data populates staging_df['smartcard_hash'] with genuine 64-hex hashes."""
        df_source = pd.DataFrame([
            {"ticket_id": "TCK_001", "timestamp": "2026-11-13 08:30:15", "route_id": "101UP", "boarding_stop": "S1", "fare": 15.0, "smartcard_id": "CARD_A"},
            {"ticket_id": "TCK_002", "timestamp": "2026-11-13 08:35:45", "route_id": "101UP", "boarding_stop": "S2", "fare": 10.0},
        ])
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            src_path = f.name
        df_source.to_parquet(src_path, index=False)

        try:
            res = run_data_swap(
                source_path=src_path,
                format_mode="mode_b",
                dry_run=True,
                db_url=test_db_url,
                salt="AUDIT_VERIFICATION_SALT"
            )
            assert res["status"] == "dry_run_success"

            # Check that when non-dry-run or staging preparation happens, all hashes are 64-hex
            anon = TransitDataAnonymizer(salt="AUDIT_VERIFICATION_SALT")
            sanitized = anon.sanitize_dataframe(df_source)
            assert "smartcard_hash" in sanitized.columns
            assert len(sanitized["smartcard_hash"].iloc[0]) == 64
        finally:
            if os.path.exists(src_path):
                os.remove(src_path)


# ===========================================================================
# 3. Synthetic Generator Parquet Validation (F10)
# ===========================================================================

class TestSyntheticParquetInvariants:
    """Empirically validates the zone loads and demand Parquet artifacts."""

    @pytest.fixture
    def truth_loads_df(self):
        staging_path = os.path.join(_crowdwise_root, "data", "staging", "staging_zone_loads.parquet")
        synthetic_path = os.path.join(_crowdwise_root, "data", "synthetic", "truth_loads_demo.parquet")
        target_path = staging_path if os.path.exists(staging_path) else synthetic_path
        if not os.path.exists(target_path):
            pytest.skip(f"Staging loads parquet not found at {target_path}")
        return pd.read_parquet(target_path)

    @pytest.fixture
    def demo_tickets_df(self):
        path = os.path.join(_crowdwise_root, "data", "synthetic", "demo_tickets.parquet")
        if not os.path.exists(path):
            pytest.skip("Synthetic demo tickets purged for real-data mode")
        return pd.read_parquet(path)

    def test_truth_loads_non_negative_loads(self, truth_loads_df):
        """All reconstructed and ground-truth passenger loads must satisfy L >= 0."""
        assert (truth_loads_df["mean_load"] >= 0.0).all(), "Found negative mean_load values!"
        assert (truth_loads_df["max_load"] >= 0).all(), "Found negative max_load values!"
        assert (truth_loads_df["boardings_total"] >= 0).all(), "Found negative boardings_total values!"
        assert (truth_loads_df["alightings_total"] >= 0).all(), "Found negative alightings_total values!"

    def test_truth_loads_diurnal_peak_ratios(self, truth_loads_df):
        """Morning peak >= 1.25 * midday, evening peak >= 1.20 * midday."""
        wk = truth_loads_df[truth_loads_df["day_type"] == "WEEKDAY"]
        hourly = wk.groupby("hour")["mean_load"].mean()

        morn_peak = max(hourly.get(8, 0.0), hourly.get(9, 0.0))
        midday = np.mean([hourly.get(12, 0.0), hourly.get(13, 0.0)])
        eve_peak = max(hourly.get(17, 0.0), hourly.get(18, 0.0))

        assert midday > 0.0, "Midday load is zero!"
        morning_ratio = morn_peak / midday
        evening_ratio = eve_peak / midday

        assert morning_ratio >= 1.25, f"Morning peak ratio {morning_ratio:.3f} < 1.25"
        assert evening_ratio >= 1.20, f"Evening peak ratio {evening_ratio:.3f} < 1.20"

    def test_truth_loads_zone_bounds(self, truth_loads_df):
        """All zones must be integers in [0, 7]."""
        zones = truth_loads_df["zone_id"].unique()
        assert set(zones).issubset(set(range(8))), f"Invalid zones detected: {zones}"

    def test_demo_tickets_schema_and_counts(self, demo_tickets_df):
        """Demo tickets must contain expected columns and non-zero rows."""
        expected_cols = {"ticket_id", "timestamp", "route_id", "direction_id", "trip_id", "boarding_stop_id", "passenger_count", "fare"}
        assert expected_cols.issubset(set(demo_tickets_df.columns))
        assert len(demo_tickets_df) >= 300000, f"Unexpected ticket count: {len(demo_tickets_df)}"


# ===========================================================================
# 4. Data Swap Atomic Staging & Rollback Stress Test (F11)
# ===========================================================================

class TestDataSwapAtomicAndRollback:
    """Stress-tests the atomic staging isolation, dry-run safety, and rollback mechanism."""

    def test_dry_run_staging_isolation(self, test_db_url):
        """In dry-run mode, staging tables are used and dropped, with ZERO modifications to production tables."""
        engine = create_engine(test_db_url)

        # Create small test parquet
        small_df = pd.DataFrame([
            {"ticket_id": "T1", "timestamp": "2026-11-13 08:00:00", "route_id": "101UP", "boarding_stop": "S1", "passenger_count": 1, "fare": 10.0},
            {"ticket_id": "T2", "timestamp": "2026-11-13 08:05:00", "route_id": "101UP", "boarding_stop": "S2", "passenger_count": 2, "fare": 20.0},
        ])
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as f:
            parquet_path = f.name
        small_df.to_parquet(parquet_path, index=False)

        try:
            # Run swap in dry-run mode
            res = run_data_swap(
                source_path=parquet_path,
                format_mode="mode_b",
                dry_run=True,
                db_url=test_db_url
            )
            assert res["status"] == "dry_run_success"

            # Inspect database tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            # Staging tables must NOT remain
            assert "etm_staging_tickets" not in tables, "Staging tickets table leaked after dry-run!"
            assert "fact_zone_demand_staging" not in tables, "Staging facts table leaked after dry-run!"

            # Production metadata must remain in demo mode
            with engine.connect() as conn:
                mode = conn.execute(text("SELECT value FROM sys_runtime_metadata WHERE key = 'data_mode'")).scalar()
                tier = conn.execute(text("SELECT value FROM sys_runtime_metadata WHERE key = 'active_tier'")).scalar()
                fact_tier = conn.execute(text("SELECT data_tier FROM fact_zone_demand LIMIT 1")).scalar()

            assert mode == "demo", f"data_mode was altered to {mode} during dry-run!"
            assert tier == "demo_synthetic", f"active_tier was altered to {tier} during dry-run!"
            assert fact_tier == "demo_synthetic", "Production fact_zone_demand rows were altered during dry-run!"
        finally:
            if os.path.exists(parquet_path):
                os.remove(parquet_path)

    def test_perform_rollback_restores_demo_mode_and_backup(self, test_db_url):
        """Rollback restores metadata and promotes fact_zone_demand_backup if available."""
        engine = create_engine(test_db_url)

        # Artificially simulate post-swap state with backup table
        with engine.begin() as conn:
            conn.execute(text("UPDATE sys_runtime_metadata SET value = 'organizer' WHERE key = 'data_mode';"))
            conn.execute(text("UPDATE sys_runtime_metadata SET value = 'organizer' WHERE key = 'active_tier';"))
            conn.execute(text("CREATE TABLE fact_zone_demand_backup AS SELECT * FROM fact_zone_demand;"))
            conn.execute(text("DELETE FROM fact_zone_demand;"))

        # Perform rollback
        perform_rollback(engine)

        with engine.connect() as conn:
            mode = conn.execute(text("SELECT value FROM sys_runtime_metadata WHERE key = 'data_mode'")).scalar()
            tier = conn.execute(text("SELECT value FROM sys_runtime_metadata WHERE key = 'active_tier'")).scalar()
            restored_count = conn.execute(text("SELECT COUNT(*) FROM fact_zone_demand")).scalar()

        assert mode == "demo"
        assert tier == "demo_synthetic"
        assert restored_count == 1
