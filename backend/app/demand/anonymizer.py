"""crowdwise/backend/app/demand/anonymizer.py
DPDP Act 2023 Compliant Privacy Engine & PII Salter.
"""
import os
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Set

DEFAULT_SALT = "CROWDWISE_DELHI_SECRET_SALT"


class TransitDataAnonymizer:
    """Zero-leakage PII sanitization and salted HMAC-SHA-256 pseudonymizer."""

    # Direct contact identifiers to be completely purged (never stored or exposed)
    PURGE_FIELDS: Set[str] = {
        "phone", "mobile", "phone_number", "passenger_mobile", "passenger_phone",
        "contact", "passenger_contact", "contact_no", "contact_number",
        "email", "passenger_email", "passenger_name", "name", "customer_name",
        "aadhaar", "aadhaar_no", "id_proof"
    }

    # Financial metadata to be purged
    FINANCIAL_FIELDS: Set[str] = {
        "upi_id", "upi_txn_id", "upi_ref", "bank_ref_no", "bank_ref", "card_pan",
        "cvv", "card_cvv", "auth_code", "payment_reference"
    }

    # Identifiers to be irreversibly pseudonymized via salted HMAC-SHA-256
    PSEUDONYMIZE_FIELDS: Set[str] = {
        "smartcard_id", "card_id", "pass_id", "pass_number",
        "ncmc_card_id", "rfid_uid", "conductor_id", "conductor_badge",
        "device_mac", "etm_device_id"
    }

    def __init__(self, salt: Optional[str] = None):
        """Initializes engine with secret salt from environment or authoritative fallback."""
        env_salt = os.getenv("CROWDWISE_ETM_SALT")
        self._default_salt = salt or env_salt or DEFAULT_SALT
        self._salt_bytes = self._default_salt.encode("utf-8")

    def hash_pii(self, raw_identifier: Optional[Any], salt: Optional[str] = None) -> str:
        """Computes irreversible HMAC-SHA-256 digest of personal identifier.

        Args:
            raw_identifier: Identifier string (phone number, card UID, pass number).
            salt: Optional salt override for isolated tenant testing.

        Returns:
            64-character lowercase hexadecimal digest, or empty string if input is falsy.
        """
        if raw_identifier is None:
            return ""
        s = str(raw_identifier).strip()
        if not s:
            return ""

        active_salt = salt.encode("utf-8") if salt else self._salt_bytes
        return hmac.new(active_salt, s.encode("utf-8"), hashlib.sha256).hexdigest()

    def hash_commuter_id(self, raw_identifier: Optional[Any], salt: Optional[str] = None) -> Optional[str]:
        """Convenience alias for commuter pseudonymization returning None for empty inputs."""
        if raw_identifier is None or not str(raw_identifier).strip():
            return None
        return self.hash_pii(raw_identifier, salt=salt)

    def truncate_timestamp_minute(self, dt: Any) -> Optional[datetime]:
        """Truncates microsecond and second precision to minute level to defeat correlation attacks."""
        if dt is None:
            return None
        import pandas as pd
        if pd.isna(dt):
            return None
        if isinstance(dt, str):
            s = dt.strip()
            if not s:
                return None
            ts = pd.to_datetime(s)
            if hasattr(ts, "tz") and ts.tz is not None:
                ts = ts.tz_localize(None)
            dt = ts.to_pydatetime()
        elif hasattr(dt, "to_pydatetime"):
            dt = dt.to_pydatetime()
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.replace(second=0, microsecond=0)

    def sanitize_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes a single telemetry dictionary according to DPDP rules.

        Steps:
        1. Strips all PURGE_FIELDS (phone, email, name, aadhaar).
        2. Strips all FINANCIAL_FIELDS (upi_txn_id, card_pan, cvv).
        3. Salt-hashes PSEUDONYMIZE_FIELDS into 64-hex digests.
        4. Truncates timestamps to minute precision if present.
        5. Preserves legitimate transit metrics.
        """
        clean: Dict[str, Any] = {}

        for k, v in raw_record.items():
            k_lower = str(k).strip().lower()

            # Step 1 & 2: Drop direct contact and financial identifiers
            if k_lower in self.PURGE_FIELDS or k_lower in self.FINANCIAL_FIELDS:
                continue

            # Step 3: Pseudonymize personal fare media and conductor IDs
            if k_lower in self.PSEUDONYMIZE_FIELDS:
                hashed_val = self.hash_pii(v)
                clean[k] = hashed_val
                if k_lower in {"smartcard_id", "card_id", "ncmc_card_id", "pass_id", "pass_number", "rfid_uid"} and "smartcard_hash" not in clean:
                    clean["smartcard_hash"] = hashed_val
                continue

            # Step 4: Timestamp precision truncation
            if isinstance(v, datetime) or (isinstance(v, str) and k_lower in {"timestamp", "datetime", "date_time", "trans_time"}):
                try:
                    clean[k] = self.truncate_timestamp_minute(v)
                    continue
                except Exception:
                    pass

            # Step 5: Retain normal field
            clean[k] = v

        return clean

    def sanitize_dataframe(self, df: Any) -> Any:
        """Vectorized or row-level sanitization for pandas DataFrames."""
        import pandas as pd
        if not isinstance(df, pd.DataFrame):
            return df
        
        out = df.copy()
        # Drop PURGE and FINANCIAL fields
        cols_to_drop = [
            c for c in out.columns
            if str(c).strip().lower() in self.PURGE_FIELDS
            or str(c).strip().lower() in self.FINANCIAL_FIELDS
        ]
        if cols_to_drop:
            out.drop(columns=cols_to_drop, inplace=True)

        # Pseudonymize card / media fields without colliding or overwriting
        media_card_cols = {
            "smartcard_id", "card_id", "ncmc_card_id", "pass_id", "pass_number", "rfid_uid"
        }
        for col in list(out.columns):
            col_clean = str(col).strip().lower()
            if col_clean in self.PSEUDONYMIZE_FIELDS:
                hashed_series = out[col].astype(str).apply(self.hash_pii)
                out[col] = hashed_series
                if col_clean in media_card_cols and "smartcard_hash" not in out.columns:
                    out["smartcard_hash"] = hashed_series

        # Truncate timestamp columns to minute precision (vectorized)
        time_keywords = {
            "timestamp", "datetime", "date_time", "trans_time",
            "boarding_time", "alighting_time"
        }
        for col in list(out.columns):
            col_clean = str(col).strip().lower()
            if col_clean in time_keywords or pd.api.types.is_datetime64_any_dtype(out[col]):
                try:
                    if pd.api.types.is_datetime64_any_dtype(out[col]):
                        out[col] = out[col].dt.floor("min")
                    else:
                        parsed = pd.to_datetime(out[col], errors="coerce")
                        if parsed.notna().any():
                            out[col] = parsed.dt.floor("min")
                        else:
                            out[col] = out[col].apply(self.truncate_timestamp_minute)
                except Exception:
                    try:
                        out[col] = out[col].apply(self.truncate_timestamp_minute)
                    except Exception:
                        pass

        return out
