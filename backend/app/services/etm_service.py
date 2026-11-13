"""crowdwise/backend/app/services/etm_service.py
Unified ETM service façade providing schema profiling, privacy filtering,
demand reconstruction (Modes A, B, C), and spatial 8-zone aggregation.
"""
import os
import math
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set, Union


import numpy as np
import pandas as pd
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from app.demand.exceptions import (
    ETMError,
    SchemaDetectionError,
    MandatoryColumnMissingError,
    CorruptDataFileError,
    EmptyStreamError,
    DataQualityThresholdExceeded,
)
from app.demand.types import (
    IngestionMode,
    QualityProfileResult,
    NormalizedTicketRecord,
    ZoneDemandRecord,
)
from app.demand.anonymizer import TransitDataAnonymizer, DEFAULT_SALT
from app.demand.profiler import ETMDataProfiler
from app.demand.alighting_model import ModeBAlightingInferenceEngine
from app.demand.reconstruction import (
    ModeAReconstructor,
    ModeCDisaggregator,
    ZoneDemandAggregator,
)
from app.models.transit import (
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimTripStart,
)

logger = logging.getLogger("crowdwise.etm_service")

# Default singleton instances
_default_anonymizer = TransitDataAnonymizer()
_default_profiler = ETMDataProfiler(anonymizer=_default_anonymizer)
_default_alighting_engine = ModeBAlightingInferenceEngine()
_default_mode_a = ModeAReconstructor()
_default_mode_c = ModeCDisaggregator()
_default_zone_aggregator = ZoneDemandAggregator()


def profile_etm_stream(data: Any, known_routes: Optional[Set[str]] = None) -> Dict[str, Any]:
    """Profiles a ticketing file path, buffer, DataFrame, or list of dicts.

    Returns:
        JSON-serializable quality profile summary dict.
    """
    profiler = ETMDataProfiler(known_routes=known_routes, anonymizer=_default_anonymizer) if known_routes else _default_profiler
    profile = profiler.profile_dataset(data)
    return profile.to_dict()


def anonymize_ticket_record(record: Dict[str, Any], salt: Optional[str] = None) -> Dict[str, Any]:
    """Applies DPDP Act 2023 compliant PII dropping and salted hashing to a single record."""
    if salt:
        anon = TransitDataAnonymizer(salt=salt)
        return anon.sanitize_record(record)
    return _default_anonymizer.sanitize_record(record)


def hash_commuter_id(identifier: Optional[Any], salt: Optional[str] = None) -> str:
    """Computes 64-character hexadecimal HMAC-SHA-256 pseudonymized hash of commuter identifier."""
    return _default_anonymizer.hash_pii(identifier, salt=salt)


def reconstruct_mode_a(pattern_stops: List[Any], tickets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Reconstructs exact on-board passenger loads from Mode A tickets (direct OD known)."""
    return _default_mode_a.reconstruct_trip(pattern_stops, tickets)


def reconstruct_mode_b(
    pattern_stops: List[Any],
    boardings_by_seq: Dict[int, int],
    reverse_boardings: Optional[Dict[int, int]] = None,
    alpha_override: Optional[float] = None,
) -> Dict[str, Any]:
    """Reconstructs on-board passenger loads via Mode B hybrid alighting inference."""
    return _default_alighting_engine.reconstruct_trip(
        pattern_stops=pattern_stops,
        boardings_by_seq=boardings_by_seq,
        reverse_boardings=reverse_boardings,
        alpha_override=alpha_override,
    )


def disaggregate_mode_c(
    pattern_stops: List[Any],
    total_passengers: int,
    stop_weights: Optional[List[float]] = None,
    reverse_boardings: Optional[Dict[int, int]] = None,
    alpha_override: Optional[float] = None,
) -> Dict[str, Any]:
    """Disaggregates Mode C aggregate demand using Hare-Niemeyer and infers alightings."""
    return _default_mode_c.reconstruct_trip(
        pattern_stops=pattern_stops,
        total_passengers=total_passengers,
        stop_weights=stop_weights,
        reverse_boardings=reverse_boardings,
        alpha_override=alpha_override,
    )


def aggregate_trip_zones(
    trip_id: str,
    route_id: str,
    direction_id: int,
    day_type: str,
    trip_date: str,
    hour: int,
    pattern_stops: List[Any],
    loads: List[float],
    boardings: List[float],
    alightings: List[float],
) -> List[Dict[str, Any]]:
    """Projects stop-level loads into 8 contiguous route corridor zones."""
    return _default_zone_aggregator.aggregate_trip_zones(
        trip_id=trip_id,
        route_id=route_id,
        direction_id=direction_id,
        day_type=day_type,
        trip_date=trip_date,
        hour=hour,
        pattern_stops=pattern_stops,
        loads=loads,
        boardings=boardings,
        alightings=alightings,
    )


class DemandReconstructionPipeline:
    """End-to-end demand reconstruction pipeline integrating with database topology."""

    def __init__(self, db_url_or_engine: Optional[Union[str, Any]] = None):
        if db_url_or_engine is None:
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            default_path = os.path.join(backend_dir, "crowdwise.db").replace("\\", "/")
            url = os.environ.get("CROWDWISE_DB_URL", f"sqlite:///{default_path}")
            self.engine = create_engine(url)
        elif isinstance(db_url_or_engine, str):
            self.engine = create_engine(db_url_or_engine)
        else:
            self.engine = db_url_or_engine

        self.profiler = ETMDataProfiler(anonymizer=_default_anonymizer)
        self.alighting_engine = ModeBAlightingInferenceEngine()
        self.mode_a_reconstructor = ModeAReconstructor()
        self.mode_c_disaggregator = ModeCDisaggregator()
        self.zone_aggregator = ZoneDemandAggregator()

    def get_pattern_stops(self, pattern_id: str) -> List[Tuple[int, str, int, float]]:
        """Retrieves ordered (seq, stop_id, zone_id, cum_dist_km) for a pattern."""
        stmt = (
            select(
                RelPatternStop.stop_sequence,
                RelPatternStop.stop_id,
                RelPatternStop.zone_id,
                RelPatternStop.cum_dist_km,
            )
            .where(RelPatternStop.pattern_id == pattern_id)
            .order_by(RelPatternStop.stop_sequence)
        )
        with Session(self.engine) as session:
            rows = session.execute(stmt).all()
            return [(int(r[0]), str(r[1]), int(r[2]), float(r[3])) for r in rows]

    def get_route_pattern_map(self) -> Dict[Tuple[str, int], str]:
        """Maps (route_id, direction_id) to the primary pattern_id."""
        stmt = select(DimRoutePattern.route_id, DimRoutePattern.direction_id, DimRoutePattern.pattern_id)
        with Session(self.engine) as session:
            rows = session.execute(stmt).all()
            return {(str(r[0]), int(r[1])): str(r[2]) for r in rows}

    def get_reverse_boardings_distribution(
        self,
        route_id: str,
        direction_id: int,
        pattern_stops: List[Tuple[int, str, int, float]],
    ) -> Dict[int, int]:
        """Approximates reverse boardings distribution by querying the reverse direction pattern stops."""
        rev_dir = 1 - direction_id
        pattern_map = self.get_route_pattern_map()
        rev_pattern_id = pattern_map.get((route_id, rev_dir))
        if not rev_pattern_id:
            return {}

        rev_stops = self.get_pattern_stops(rev_pattern_id)
        if not rev_stops:
            return {}

        rev_stop_ids = {s[1]: s[0] for s in rev_stops}
        rev_boardings: Dict[int, int] = {}
        for fwd_seq, stop_id, _, _ in pattern_stops:
            if stop_id in rev_stop_ids:
                rev_boardings[fwd_seq] = 10  # default baseline symmetry
            else:
                rev_boardings[fwd_seq] = 0

        return rev_boardings

    def process_ticket_stream(
        self,
        data: Any,
        mode: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], pd.DataFrame]:
        """Profiles, validates, reconstructs demand, and aggregates into zones.

        Returns:
            Tuple of:
              - trip_zone_records: List of trip-level zone demand dicts (truth loads)
              - hourly_zone_df: DataFrame of hourly aggregated zone demands
        """
        if isinstance(data, pd.DataFrame) and "timestamp_iso" in data.columns and "route_id" in data.columns:
            df_records = data
        else:
            df_records = self.profiler.ingest_dataframe(data)

        if df_records.empty:
            return [], pd.DataFrame()

        detected_mode = mode or ("mode_a" if "alighting_stop_id" in df_records.columns and df_records["alighting_stop_id"].notna().any() else "mode_b")

        pattern_map = self.get_route_pattern_map()
        trip_zone_records: List[Dict[str, Any]] = []


        # Group by trip if available, or by (route_id, direction_id, day_type, hour, date)
        has_trip = "trip_id" in df_records.columns and df_records["trip_id"].notna().any()
        group_cols = ["trip_id", "route_id", "direction_id", "day_type", "hour"] if has_trip else ["route_id", "direction_id", "day_type", "hour"]

        # Cache pattern stops and reverse boardings across trips
        cached_pat_stops: Dict[str, List[Tuple[int, str, int, float]]] = {}
        cached_rev_boardings: Dict[Tuple[str, int], Dict[int, int]] = {}

        for grp_keys, grp in df_records.groupby(group_cols):
            if has_trip:
                t_id, r_id, d_id, dt, hr = grp_keys
            else:
                r_id, d_id, dt, hr = grp_keys
                t_id = f"SYN_{r_id}_{d_id}_{dt}_{hr}"

            pat_id = pattern_map.get((r_id, d_id))
            if not pat_id:
                continue

            if pat_id not in cached_pat_stops:
                cached_pat_stops[pat_id] = self.get_pattern_stops(pat_id)
            pat_stops = cached_pat_stops[pat_id]
            if not pat_stops:
                continue

            first_dt = grp["timestamp"].iloc[0]
            trip_date = first_dt.strftime("%Y-%m-%d") if isinstance(first_dt, datetime) else str(first_dt)[:10]

            if detected_mode == "mode_a":
                tickets = grp.to_dict(orient="records")
                recon = self.mode_a_reconstructor.reconstruct_trip(pat_stops, tickets)
            else:
                stop_seq_map = {s[1]: s[0] for s in pat_stops}
                boardings_by_seq: Dict[int, int] = defaultdict(int)

                # Vectorized sum by boarding stop
                b_counts = grp.groupby("boarding_stop_id")["passenger_count"].sum().to_dict()
                for b_id, cnt in b_counts.items():
                    seq = stop_seq_map.get(str(b_id))
                    if seq is not None:
                        boardings_by_seq[seq] += int(cnt)

                cache_key = (r_id, d_id)
                if cache_key not in cached_rev_boardings:
                    cached_rev_boardings[cache_key] = self.get_reverse_boardings_distribution(r_id, d_id, pat_stops)
                rev_boardings = cached_rev_boardings[cache_key]

                recon = self.alighting_engine.reconstruct_trip(
                    pattern_stops=pat_stops,
                    boardings_by_seq=boardings_by_seq,
                    reverse_boardings=rev_boardings,
                )

            zones = self.zone_aggregator.aggregate_trip_zones(

                trip_id=str(t_id),
                route_id=str(r_id),
                direction_id=int(d_id),
                day_type=str(dt),
                trip_date=trip_date,
                hour=int(hr),
                pattern_stops=pat_stops,
                loads=recon["loads"],
                boardings=recon["boardings"],
                alightings=recon["alightings"],
            )
            trip_zone_records.extend(zones)

        hourly_df = self.zone_aggregator.aggregate_hourly_zones(trip_zone_records)
        return trip_zone_records, hourly_df
