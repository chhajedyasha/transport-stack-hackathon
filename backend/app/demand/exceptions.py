"""crowdwise/backend/app/demand/exceptions.py
Structured exception classes for ETM ingestion, profiling, and privacy enforcement.
"""
from typing import List, Optional, Dict, Any


class ETMError(Exception):
    """Base exception for all ETM pipeline errors."""
    pass


class SchemaDetectionError(ETMError):
    """Raised when incoming dataset schema cannot be matched to Mode A, B, or C."""
    def __init__(self, message: str, detected_columns: Optional[List[str]] = None):
        super().__init__(message)
        self.detected_columns = detected_columns or []


class MandatoryColumnMissingError(ETMError):
    """Raised when mandatory common columns (timestamp, route_id) are absent."""
    def __init__(self, missing_columns: List[str]):
        super().__init__(f"Mandatory columns missing from telemetry stream: {missing_columns}")
        self.missing_columns = missing_columns


class CorruptDataFileError(ETMError):
    """Raised when data file is corrupted (e.g. zero bytes, missing Parquet magic bytes)."""
    pass


class EmptyStreamError(CorruptDataFileError):
    """Raised when data file or telemetry stream contains zero records."""
    pass


class DataQualityThresholdExceeded(ETMError):
    """Raised when null rates or timestamp error rates exceed acceptable thresholds."""
    def __init__(self, message: str, diagnostics: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.diagnostics = diagnostics or {}
