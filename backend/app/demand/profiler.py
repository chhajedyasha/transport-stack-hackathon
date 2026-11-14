"""crowdwise/backend/app/demand/profiler.py
Schema-Agnostic Ingestion Profiler & Data Quality Validator for ETM Telemetry.
"""
import io
import os
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Set, Union
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from app.demand.exceptions import (
    ETMError,
    SchemaDetectionError,
    MandatoryColumnMissingError,
    CorruptDataFileError,
    EmptyStreamError,
    DataQualityThresholdExceeded,
)
from app.demand.types import IngestionMode, QualityProfileResult, NormalizedTicketRecord
from app.demand.anonymizer import TransitDataAnonymizer



class ETMDataProfiler:
    """Profiles raw ticketing feeds, validates constraints, and normalizes telemetry streams."""

    COLUMN_SYNONYMS: Dict[str, Set[str]] = {
        "ticket_id": {"ticket_id", "ticket_no", "ticketid", "txn_id", "transaction_id", "rec_id"},
        "timestamp": {
            "timestamp", "trans_time", "transaction_time", "datetime", "date_time", "ticket_time",
            "issue_time", "time", "date", "trip_date", "created_at"
        },
        "route_id": {"route_id", "route_short_name", "route_name", "route", "route_no", "line_id"},
        "direction_id": {"direction_id", "direction", "dir", "trip_dir"},
        "trip_id": {"trip_id", "trip_no", "scheduled_trip_id"},
        "boarding_stop_id": {
            "boarding_stop_id", "origin_stop_id", "from_stop_id", "from_stop", "boarding_stop",
            "origin", "src_stop", "source_stop", "start_stop_id", "stage_id", "origin_seq",
            "start_stop_name", "start_stop"
        },
        "alighting_stop_id": {
            "alighting_stop_id", "destination_stop_id", "dest_stop_id", "dest_stop", "to_stop_id",
            "alighting_stop", "destination", "dest", "end_stop_id", "dest_seq",
            "end_stop_name", "end_stop"
        },
        "passenger_count": {
            "passenger_count", "passengers", "count", "pax", "ticket_count", "quantity", "pax_count"
        },
        "total_passengers": {
            "total_passengers", "total_pax", "total_count", "boardings", "daily_load",
            "aggregate_passengers", "daily_boardings", "daily_passengers", "daily_total"
        },
        "fare_paid": {
            "fare_paid", "fare", "fare_amount", "amount", "ticket_amount", "ticket_price", "price"
        },
        "fare_stage": {"fare_stage", "stage", "stage_no"},
    }

    def __init__(self, known_routes: Optional[Set[str]] = None, anonymizer: Optional[TransitDataAnonymizer] = None):
        """Initializes profiler with optional known route set and anonymizer."""
        self.known_routes = known_routes or set()
        self.anonymizer = anonymizer or TransitDataAnonymizer()

    def is_pii_or_financial_field(self, field_name: str) -> bool:
        """Determines if a field is direct contact PII or sensitive financial data to be purged."""
        c = str(field_name).strip().lower()
        if c in self.anonymizer.PURGE_FIELDS or c in self.anonymizer.FINANCIAL_FIELDS:
            return True

        # Explicitly check for direct contact PII and financial identifiers
        pii_tokens = {
            "name", "passenger_name", "customer_name", "commuter_name", "user_name",
            "full_name", "first_name", "last_name",
            "phone", "passenger_phone", "passenger_mobile", "mobile", "contact",
            "phone_number", "phone_no", "mobile_no", "contact_no", "contact_number",
            "email", "passenger_email", "customer_email", "user_email", "mail",
            "aadhaar", "aadhaar_no", "aadhaar_number", "aadhar", "aadhar_no", "uidai",
            "card_pan", "pan", "card_number", "card_no", "card_num", "credit_card", "debit_card",
            "cvv", "card_cvv",
            "upi_id", "upi_txn_id", "upi_txn", "upi_ref", "upi", "vpa",
            "bank_ref", "bank_ref_no", "account_no", "account_number"
        }
        if c in pii_tokens:
            return True

        # Check substring matches
        pii_substrings = [
            "passenger_name", "customer_name", "commuter_name", "user_name",
            "passenger_phone", "passenger_mobile", "customer_phone", "customer_mobile",
            "passenger_email", "customer_email", "passenger_contact",
            "phone", "mobile", "email", "aadhaar", "aadhar",
            "upi_id", "upi_txn", "upi_ref", "card_pan", "cvv", "bank_ref",
            "contact_no", "contact_num", "card_num", "card_number", "credit_card", "debit_card"
        ]
        if any(sub in c for sub in pii_substrings):
            return True

        # Standalone name or ending in _name, without capturing operational route/stop/agency/trip metadata
        if c == "name" or (c.endswith("_name") and not any(c.startswith(p) for p in ["route", "stop", "station", "agency", "line", "trip", "zone"])):
            return True

        if c == "contact":
            return True

        return False

    def map_columns(self, raw_columns: List[str]) -> Dict[str, str]:
        """Maps incoming raw column names to canonical internal names using synonyms."""
        mapped: Dict[str, str] = {}
        used_canonicals: Set[str] = set()

        for raw_col in raw_columns:
            cleaned = str(raw_col).strip().lower()
            found = False
            for canonical, synonyms in self.COLUMN_SYNONYMS.items():
                if (cleaned in synonyms or cleaned == canonical) and canonical not in used_canonicals:
                    mapped[raw_col] = canonical
                    used_canonicals.add(canonical)
                    found = True
                    break
            if not found:
                mapped[raw_col] = str(raw_col).strip()
        return mapped

    def detect_mode(self, canonical_cols: Set[str]) -> IngestionMode:
        """Determines ingestion mode from mapped canonical columns."""
        if "timestamp" not in canonical_cols or "route_id" not in canonical_cols:
            missing = [c for c in ["timestamp", "route_id"] if c not in canonical_cols]
            raise MandatoryColumnMissingError(missing)

        has_boarding = "boarding_stop_id" in canonical_cols
        has_alighting = "alighting_stop_id" in canonical_cols
        has_aggregate = "total_passengers" in canonical_cols or (
            "passenger_count" in canonical_cols and not has_boarding
        )

        if has_boarding and has_alighting:
            return "mode_a"
        elif has_boarding:
            return "mode_b"
        elif has_aggregate:
            return "mode_c"
        else:
            raise SchemaDetectionError(
                "Unable to identify ETM operational mode. Expected boarding stop (Mode A/B) or aggregate passenger volume (Mode C).",
                list(canonical_cols)
            )

    def validate_file_integrity(self, file_path: str) -> str:
        """Verifies file existence, non-zero size, and Parquet magic bytes if applicable."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if os.path.getsize(file_path) == 0:
            raise CorruptDataFileError(f"Target file is empty (zero bytes): {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".parquet", ".pq"):
            file_size = os.path.getsize(file_path)
            if file_size < 8:
                raise CorruptDataFileError(f"Corrupt Parquet file: file smaller than 8 bytes in {file_path}")
            with open(file_path, "rb") as f:
                header = f.read(4)
                f.seek(file_size - 4)
                footer = f.read(4)
                if header != b"PAR1" or footer != b"PAR1":
                    raise CorruptDataFileError(f"Corrupt Parquet file: missing 'PAR1' magic bytes in {file_path}")
        return ext

    def parse_timestamp(self, raw_time: Any) -> Optional[datetime]:
        """Normalizes ISO-8601 strings, Unix epoch numbers, post-midnight, or Indian format timestamps to UTC datetime."""
        if raw_time is None or pd.isna(raw_time):
            return None

        # Handle numeric epoch seconds or milliseconds
        if isinstance(raw_time, (int, float, np.integer, np.floating)):
            try:
                val = float(raw_time)
                if val > 1e11:  # Milliseconds epoch
                    val = val / 1000.0
                return datetime.fromtimestamp(val, timezone.utc)
            except Exception:
                return None

        # Handle datetime objects
        if isinstance(raw_time, datetime):
            if raw_time.tzinfo is None:
                return raw_time.replace(tzinfo=timezone.utc)
            return raw_time.astimezone(timezone.utc)

        # Handle strings
        s = str(raw_time).strip()
        if not s:
            return None

        # Handle post-midnight hours >= 24 (e.g. "2026-11-13 24:15:00" or "24:15:00")
        post_midnight_match = re.search(r"(\b)(\d{2}):(\d{2}):(\d{2})", s)
        if post_midnight_match:
            hour_val = int(post_midnight_match.group(2))
            if hour_val >= 24:
                adjusted_hour = hour_val - 24
                days_add = 1 + (adjusted_hour // 24)
                rem_hour = adjusted_hour % 24
                s_adj = s[:post_midnight_match.start(2)] + f"{rem_hour:02d}" + s[post_midnight_match.end(2):]
                try:
                    dt = pd.to_datetime(s_adj, utc=True).to_pydatetime()
                    return dt + timedelta(days=days_add)
                except Exception:
                    pass

        try:
            # ISO-8601 or standard pandas datetime
            if "T" in s or "-" in s:
                dt = pd.to_datetime(s, utc=True)
                return dt.to_pydatetime()
            # Indian DD/MM/YYYY format
            elif "/" in s:
                dt = pd.to_datetime(s, format="%d/%m/%Y %H:%M:%S", errors="coerce")
                if pd.notna(dt):
                    return dt.tz_localize("Asia/Kolkata").tz_convert("UTC").to_pydatetime()
                dt_fallback = pd.to_datetime(s, utc=True, errors="coerce")
                if pd.notna(dt_fallback):
                    return dt_fallback.to_pydatetime()
        except Exception:
            pass

        return None

    def load_stream(self, data: Any) -> pd.DataFrame:
        """Loads data from file path, buffer, list of dicts, or DataFrame into a pandas DataFrame."""
        if isinstance(data, pd.DataFrame):
            if data.empty:
                raise EmptyStreamError("Supplied DataFrame is empty.")
            return data.copy()

        if isinstance(data, list):
            if not data:
                raise EmptyStreamError("Supplied list is empty.")
            return pd.DataFrame(data)

        if isinstance(data, (io.StringIO, io.BytesIO)):
            content = data.getvalue() if hasattr(data, "getvalue") else data.read()
            if len(content) == 0:
                raise EmptyStreamError("Stream buffer is empty (0 bytes).")
            if isinstance(data, io.BytesIO):
                if content.startswith(b"PAR1"):
                    return pd.read_parquet(data)
                return pd.read_csv(data)
            return pd.read_csv(data)

        if isinstance(data, str):
            if not os.path.exists(data):
                raise FileNotFoundError(f"Source file does not exist: {data}")
            ext = self.validate_file_integrity(data)
            if ext in (".parquet", ".pq"):
                df = pd.read_parquet(data)
            else:
                df = pd.read_csv(data)
            if df.empty:
                raise EmptyStreamError(f"Target file {data} contains 0 rows.")
            return df

        raise ValueError(f"Unsupported data source type: {type(data)}")

    def profile_dataset(self, data: Any) -> QualityProfileResult:
        """Performs comprehensive profiling, null rate checks, and anomaly detection."""
        df = self.load_stream(data)
        total_rows = len(df)
        if total_rows == 0:
            raise EmptyStreamError("Dataset contains zero rows.")

        col_mapping = self.map_columns(list(df.columns))
        renamed_df = df.rename(columns=col_mapping)
        canonical_cols = set(renamed_df.columns)

        mode = self.detect_mode(canonical_cols)

        # Check null rates
        null_rates = {str(col): float(renamed_df[col].isnull().mean()) for col in renamed_df.columns}

        # Timestamp evaluation
        if pd.api.types.is_datetime64_any_dtype(renamed_df["timestamp"]):
            parsed_times = pd.to_datetime(renamed_df["timestamp"], utc=True)
        else:
            try:
                parsed_times = pd.to_datetime(renamed_df["timestamp"], utc=True, errors="coerce")
                failed_mask = parsed_times.isnull() & renamed_df["timestamp"].notna()
                if failed_mask.any():
                    fallback_times = renamed_df.loc[failed_mask, "timestamp"].apply(self.parse_timestamp)
                    parsed_times = parsed_times.combine_first(fallback_times)
            except Exception:
                parsed_times = renamed_df["timestamp"].apply(self.parse_timestamp)

        invalid_times = int(parsed_times.isnull().sum())
        valid_time_rate = float(1.0 - (invalid_times / max(1, total_rows)))

        valid_times_series = parsed_times.dropna()
        now_utc = datetime.now(timezone.utc) + timedelta(minutes=5)
        future_times_count = int((valid_times_series > now_utc).sum())

        # Negative fare evaluation
        negative_fares_count = 0
        if "fare_paid" in renamed_df.columns:
            fares = pd.to_numeric(renamed_df["fare_paid"], errors="coerce")
            negative_fares_count = int((fares < 0.0).sum())

        # Route validation
        unmatched_count = 0
        routes_list = []
        if "route_id" in renamed_df.columns:
            routes_list = renamed_df["route_id"].dropna().astype(str).unique().tolist()
            if self.known_routes:
                unmatched = [r for r in routes_list if r not in self.known_routes]
                unmatched_count = len(unmatched)

        unmatched_rate = float(unmatched_count / max(1, len(routes_list))) if self.known_routes else 0.0

        # Overall quality pass verdict
        quality_pass = bool(
            invalid_times == 0
            and null_rates.get("route_id", 1.0) == 0.0
            and future_times_count == 0
            and negative_fares_count == 0
        )

        return QualityProfileResult(
            mode=mode,
            total_records=total_rows,
            valid_records=total_rows - invalid_times,
            invalid_records=invalid_times,
            valid_timestamp_rate=valid_time_rate,
            time_min=valid_times_series.min().isoformat() if not valid_times_series.empty else None,
            time_max=valid_times_series.max().isoformat() if not valid_times_series.empty else None,
            null_rates=null_rates,
            unmatched_routes_count=unmatched_count,
            unmatched_routes_rate=unmatched_rate,
            quality_pass=quality_pass,
            diagnostics={
                "future_timestamps_detected": future_times_count,
                "negative_fares_detected": negative_fares_count,
                "unmatched_routes": unmatched_count,
            }
        )

    def ingest_dataframe(self, data: Any) -> pd.DataFrame:
        """Vectorized ingestion, validation, anonymization, and normalization returning clean DataFrame."""
        df = self.load_stream(data)
        col_mapping = self.map_columns(list(df.columns))
        canonical_df = df.rename(columns=col_mapping)
        mode = self.detect_mode(set(canonical_df.columns))

        from app.services.direction_resolver import resolve_direction

        # Vectorized timestamp parsing
        if pd.api.types.is_datetime64_any_dtype(canonical_df["timestamp"]):
            parsed_series = pd.to_datetime(canonical_df["timestamp"], utc=True)
        else:
            parsed_series = pd.to_datetime(canonical_df["timestamp"], utc=True, errors="coerce")
            failed_mask = parsed_series.isnull() & canonical_df["timestamp"].notna()
            if failed_mask.any():
                fallback_times = canonical_df.loc[failed_mask, "timestamp"].apply(self.parse_timestamp)
                parsed_series = parsed_series.combine_first(fallback_times)

        now_utc = datetime.now(timezone.utc) + timedelta(minutes=5)
        valid_mask = (
            parsed_series.notna()
            & (parsed_series <= now_utc)
            & canonical_df["route_id"].notna()
            & (canonical_df["route_id"].astype(str).str.strip() != "")
        )

        if "fare_paid" in canonical_df.columns:
            fares = pd.to_numeric(canonical_df["fare_paid"], errors="coerce").fillna(0.0)
            valid_mask = valid_mask & (fares >= 0.0)
            canonical_df["fare_paid"] = fares
        elif "fare" in canonical_df.columns:
            fares = pd.to_numeric(canonical_df["fare"], errors="coerce").fillna(0.0)
            valid_mask = valid_mask & (fares >= 0.0)
            canonical_df["fare_paid"] = fares
        else:
            canonical_df["fare_paid"] = 0.0

        clean_df = canonical_df[valid_mask].copy()
        clean_df["timestamp"] = parsed_series[valid_mask].dt.floor("min")
        clean_df["timestamp_iso"] = clean_df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        clean_df["hour"] = clean_df["timestamp"].dt.hour
        wday = clean_df["timestamp"].dt.weekday
        clean_df["day_type"] = np.where(wday < 5, "WEEKDAY", np.where(wday == 5, "SATURDAY", "SUNDAY"))

        if "direction_id" not in clean_df.columns or clean_df["direction_id"].isnull().all():
            clean_df["direction_id"] = clean_df["route_id"].astype(str).apply(resolve_direction)
        else:
            clean_df["direction_id"] = pd.to_numeric(clean_df["direction_id"], errors="coerce").fillna(0).astype(int)

        if "passenger_count" not in clean_df.columns:
            clean_df["passenger_count"] = 1
        else:
            clean_df["passenger_count"] = pd.to_numeric(clean_df["passenger_count"], errors="coerce").fillna(1).astype(int)

        # Ticket ID sanitization if personal fare media
        if "ticket_id" in clean_df.columns:
            tids = clean_df["ticket_id"].astype(str)
            needs_hash = tids.str.lower().str.contains("phone|card|pass|aadhaar|\\+91", regex=True)
            if needs_hash.any():
                clean_df.loc[needs_hash, "ticket_id"] = tids[needs_hash].apply(self.anonymizer.hash_pii)
        else:
            clean_df["ticket_id"] = [f"TK_{i}" for i in range(len(clean_df))]

        # Purge direct contact identifiers and sensitive financial columns
        pii_cols = [c for c in clean_df.columns if self.is_pii_or_financial_field(c)]
        if pii_cols:
            clean_df.drop(columns=pii_cols, inplace=True)

        return clean_df

    def ingest_records(self, data: Any) -> List[NormalizedTicketRecord]:
        """Ingests raw data stream, validates, anonymizes, and normalizes into ticket records."""
        clean_df = self.ingest_dataframe(data)

        # Build records from pre-sanitized clean_df
        records: List[NormalizedTicketRecord] = []
        standard_cols = {
            "ticket_id", "timestamp", "timestamp_iso", "route_id", "direction_id",
            "day_type", "hour", "boarding_stop_id", "alighting_stop_id",
            "passenger_count", "fare_paid", "fare_stage", "trip_id"
        }
        for row in clean_df.to_dict(orient="records"):
            vendor_meta = {}
            for k, v in row.items():
                if k == "vendor_metadata" and isinstance(v, dict):
                    for mk, mv in v.items():
                        if pd.notna(mv) and not self.is_pii_or_financial_field(mk):
                            vendor_meta[mk] = mv
                elif k not in standard_cols and pd.notna(v) and not self.is_pii_or_financial_field(k):
                    vendor_meta[k] = v
            records.append(NormalizedTicketRecord(
                ticket_id=str(row["ticket_id"]),
                timestamp=row["timestamp"].to_pydatetime() if hasattr(row["timestamp"], "to_pydatetime") else row["timestamp"],
                timestamp_iso=str(row["timestamp_iso"]),
                route_id=str(row["route_id"]),
                direction_id=int(row["direction_id"]),
                day_type=str(row["day_type"]),
                hour=int(row["hour"]),
                boarding_stop_id=str(row["boarding_stop_id"]) if "boarding_stop_id" in row and pd.notna(row["boarding_stop_id"]) else None,
                alighting_stop_id=str(row["alighting_stop_id"]) if "alighting_stop_id" in row and pd.notna(row["alighting_stop_id"]) else None,
                passenger_count=int(row["passenger_count"]),
                fare_paid=float(row.get("fare_paid", 0.0)),
                fare_stage=int(row["fare_stage"]) if "fare_stage" in row and pd.notna(row["fare_stage"]) else None,
                vendor_metadata=vendor_meta,
            ))

        return records

