"""crowdwise/backend/app/demand/reconstruction.py
Features F07, F09, and Spatial 8-Zone Demand Reconstruction.
"""
import math
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from app.demand.alighting_model import ModeBAlightingInferenceEngine


class ModeAReconstructor:
    """F07: Mode A (Full Origin-Destination Known) direct passenger load reconstruction."""

    @staticmethod
    def reconstruct_trip(
        pattern_stops: List[Any],
        tickets: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Reconstructs exact on-board passenger loads from Mode A ticketing records.

        Args:
            pattern_stops: List of tuples (seq, stop_id, zone_id, cum_dist) or objects.
            tickets: List of ticket records containing origin and destination stops.

        Returns:
            Dict containing 'boardings', 'alightings', 'loads', and 'od_matrix'.
        """
        n = len(pattern_stops)
        if n == 0:
            return {
                "boardings": [],
                "alightings": [],
                "loads": [],
                "od_matrix": np.zeros((0, 0)),
            }

        import re

        def _clean_tokens(s: str) -> set:
            s = s.lower().replace("s.j.", "safdarjung").replace("sj ", "safdarjung ").strip()
            s = re.sub(r'\b(terminal|metro station|crossing|bus stand|stand|dtc|\(t\)|flats|dda flats|village|more|road|rd)\b', '', s)
            return set(re.findall(r'[a-z0-9]+', s))

        token_to_seq: List[Tuple[set, int]] = []
        stop_id_to_seq: Dict[str, int] = {}
        for idx, s in enumerate(pattern_stops):
            if isinstance(s, (tuple, list)):
                stop_seq = int(s[0])
                stop_id = str(s[1])
                stop_name = str(s[4]) if len(s) > 4 else ""
            elif isinstance(s, dict):
                stop_seq = int(s.get("stop_sequence", s.get("seq", idx)))
                stop_id = str(s.get("stop_id", f"S_{idx}"))
                stop_name = str(s.get("stop_name", ""))
            else:
                stop_seq = int(getattr(s, "stop_sequence", getattr(s, "seq", idx)))
                stop_id = str(getattr(s, "stop_id", f"S_{idx}"))
                stop_name = str(getattr(s, "stop_name", ""))
            stop_id_to_seq[stop_id] = stop_seq
            stop_id_to_seq[str(stop_seq)] = stop_seq
            if stop_name:
                stop_id_to_seq[stop_name.strip()] = stop_seq
                stop_id_to_seq[stop_name.lower().strip()] = stop_seq
                toks = _clean_tokens(stop_name)
                if toks:
                    token_to_seq.append((toks, stop_seq))

        def _resolve_stop(val: Any) -> Optional[int]:
            if val is None:
                return None
            val_str = str(val).strip()
            if val_str in stop_id_to_seq:
                return stop_id_to_seq[val_str]
            val_lower = val_str.lower()
            if val_lower in stop_id_to_seq:
                return stop_id_to_seq[val_lower]
            if val_str.isdigit() and int(val_str) < n:
                return int(val_str)
            val_toks = _clean_tokens(val_str)
            if val_toks:
                best_seq = None
                best_overlap = 0
                for toks, seq in token_to_seq:
                    overlap = len(val_toks & toks)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_seq = seq
                if best_overlap > 0:
                    return best_seq
            return None

        # 1. Accumulate OD Matrix
        od_matrix = np.zeros((n, n), dtype=np.float64)
        total_tickets = len(tickets)
        matched_tickets = 0
        for t in tickets:
            origin = t.get("boarding_stop_id") or t.get("origin") or t.get("origin_seq") or t.get("from_stop_id") or t.get("start_stop_name")
            dest = t.get("alighting_stop_id") or t.get("dest") or t.get("destination") or t.get("dest_seq") or t.get("to_stop_id") or t.get("end_stop_name")
            count = float(t.get("passenger_count", t.get("passengers", t.get("count", 1))))

            i = _resolve_stop(origin)
            j = _resolve_stop(dest)

            if i is not None and j is not None and 0 <= i < n and 0 <= j < n:
                matched_tickets += 1
                if i < j:
                    od_matrix[i, j] += count
                # If i == j, same-stop boarding & alighting cancels out with 0 net load contribution

        # 2. Derive Boardings and Alightings
        boardings = np.sum(od_matrix, axis=1)  # B_i
        alightings = np.sum(od_matrix, axis=0)  # A_j

        # 3. Accumulate On-Board Passenger Loads
        loads = np.zeros(n, dtype=np.float64)
        curr_load = 0.0
        for s in range(n):
            curr_load = curr_load + boardings[s] - alightings[s]
            loads[s] = max(0.0, curr_load)

        # Terminal conservation clearance
        loads[n - 1] = 0.0

        return {
            "boardings": boardings.tolist(),
            "alightings": alightings.tolist(),
            "loads": loads.tolist(),
            "od_matrix": od_matrix,
            "total_tickets": total_tickets,
            "unmatched_tickets": total_tickets - matched_tickets,
        }


class ModeCDisaggregator:
    """F09: Mode C (Route/Trip Aggregate Demand) disaggregation via Largest Remainder Method."""

    @staticmethod
    def disaggregate_hare_niemeyer(
        total_passengers: int,
        stop_weights: List[float],
    ) -> List[int]:
        """Disaggregates aggregate demand into integer stop boardings conserving the total sum strictly.

        Guarantees:
        - sum(allocated) == total_passengers
        - allocated[i] >= 0 for all i
        - integer passenger counts
        """
        if total_passengers <= 0 or not stop_weights:
            return [0] * len(stop_weights)

        n = len(stop_weights)
        sum_weights = sum(stop_weights)
        if sum_weights <= 0:
            normalized_weights = [1.0 / n] * n
        else:
            normalized_weights = [w / sum_weights for w in stop_weights]

        # Step 1: Exact quotas and integer base
        quotas = [total_passengers * w for w in normalized_weights]
        base = [math.floor(q) for q in quotas]
        remainders = [(quotas[i] - base[i], i) for i in range(n)]

        # Step 2: Remainder deficit
        deficit = total_passengers - sum(base)

        # Step 3: Distribute +1 to stops with largest remainders
        remainders.sort(key=lambda x: x[0], reverse=True)
        allocated = list(base)
        for k in range(deficit):
            idx = remainders[k][1]
            allocated[idx] += 1

        assert sum(allocated) == total_passengers
        return allocated

    def reconstruct_trip(
        self,
        pattern_stops: List[Any],
        total_passengers: int,
        stop_weights: Optional[List[float]] = None,
        reverse_boardings: Optional[Dict[int, int]] = None,
        alpha_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Disaggregates Mode C total passengers across stops and runs Mode B alighting inference."""
        n = len(pattern_stops)
        if n == 0:
            return {"boardings": [], "alightings": [], "loads": []}

        if stop_weights is None or len(stop_weights) != n:
            # Cold-start uniform weights across interior stops; terminus has 0 boarding weight
            if n > 1:
                weights = [1.0 / (n - 1)] * (n - 1) + [0.0]
            else:
                weights = [1.0]
        else:
            weights = list(stop_weights)
            if len(weights) > 1:
                weights[-1] = 0.0  # Terminal stop clearance: zero boardings at terminus

        boardings_list = self.disaggregate_hare_niemeyer(total_passengers, weights)
        boardings_dict = {i: boardings_list[i] for i in range(n)}

        inference_engine = ModeBAlightingInferenceEngine()
        return inference_engine.reconstruct_trip(
            pattern_stops=pattern_stops,
            boardings_by_seq=boardings_dict,
            reverse_boardings=reverse_boardings,
            alpha_override=alpha_override,
        )

    def disaggregate_daily_route_demand(
        self,
        daily_total_passengers: int,
        scheduled_trip_profiles: List[Tuple[str, int, List[float]]],
    ) -> List[Dict[str, Any]]:
        """Disaggregates daily route total passengers across scheduled trips and pattern stops.

        Args:
            daily_total_passengers: Aggregate daily boardings for route.
            scheduled_trip_profiles: List of (trip_id, departure_hour, stop_weights).

        Returns:
            List of dicts: {"trip_id": str, "hour": int, "boardings": Dict[int, int], "total_passengers": int}
        """
        if not scheduled_trip_profiles or daily_total_passengers <= 0:
            return []

        # 1. Disaggregate across trips based on trip sum weights
        trip_weights = [sum(profile[2]) for profile in scheduled_trip_profiles]
        trip_totals = self.disaggregate_hare_niemeyer(daily_total_passengers, trip_weights)

        # 2. For each trip, disaggregate its total across stops
        result = []
        for (trip_id, hour, stop_weights), trip_total in zip(scheduled_trip_profiles, trip_totals):
            stop_boardings = self.disaggregate_hare_niemeyer(trip_total, stop_weights)
            result.append({
                "trip_id": trip_id,
                "hour": hour,
                "boardings": {i: b for i, b in enumerate(stop_boardings)},
                "total_passengers": trip_total,
            })
        return result


class ZoneDemandAggregator:
    """Spatial Aggregation of stop-level loads into 8 contiguous corridor zones."""

    @staticmethod
    def zone_partition(stop_sequence: int, total_stops: int) -> int:
        """Closed-form 8-zone partition formula: min(7, floor(8 * s / N)) for N > 8."""
        if total_stops <= 0:
            return 0
        if total_stops <= 8:
            return min(7, max(0, stop_sequence))
        return min(7, max(0, math.floor((stop_sequence * 8) / total_stops)))

    def get_zone_for_stop(self, stop_sequence: int, total_stops: int) -> int:
        """Instance alias for zone_partition."""
        return self.zone_partition(stop_sequence, total_stops)

    @classmethod
    def aggregate_trip_zones(
        cls,
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
        """Aggregates stop-level metrics into up to 8 contiguous zones for a single trip."""
        n = len(pattern_stops)
        zone_stops: Dict[int, List[int]] = defaultdict(list)

        for s in range(n):
            item = pattern_stops[s]
            if isinstance(item, (tuple, list)) and len(item) > 2:
                z = int(item[2])
            elif isinstance(item, dict) and "zone_id" in item:
                z = int(item["zone_id"])
            elif hasattr(item, "zone_id"):
                z = int(getattr(item, "zone_id"))
            else:
                z = cls.zone_partition(s, n)
            zone_stops[z].append(s)

        results: List[Dict[str, Any]] = []
        for z in sorted(zone_stops.keys()):
            indices = zone_stops[z]
            z_loads = [loads[i] for i in indices if i < len(loads)]
            z_boardings = [boardings[i] for i in indices if i < len(boardings)]
            z_alightings = [alightings[i] for i in indices if i < len(alightings)]

            if not z_loads:
                continue

            mean_val = float(np.mean(z_loads))
            max_val = int(np.max(z_loads))
            b_total = int(round(float(np.sum(z_boardings))))
            a_total = int(round(float(np.sum(z_alightings))))

            results.append({
                "trip_id": str(trip_id),
                "route_id": str(route_id),
                "direction_id": int(direction_id),
                "day_type": str(day_type),
                "trip_date": str(trip_date),
                "date": str(trip_date),
                "hour": int(hour),
                "zone_id": int(z),
                "mean_load": round(mean_val, 2),
                "max_load": max_val,
                "boardings_total": b_total,
                "alightings_total": a_total,
                "trip_count": 1,
            })

        return results

    @staticmethod
    def aggregate_hourly_zones(trip_zone_records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Aggregates trip-level zone records into the hourly zone loads schema for ML training."""
        if not trip_zone_records:
            return pd.DataFrame(columns=[
                "route_id", "direction_id", "zone_id", "day_type",
                "hour", "trip_date", "mean_load", "trip_count"
            ])

        df = pd.DataFrame(trip_zone_records)
        grouped = df.groupby(
            ["route_id", "direction_id", "zone_id", "day_type", "hour", "trip_date"],
            as_index=False
        ).agg(
            mean_load=("mean_load", "mean"),
            max_load=("max_load", "max"),
            boardings_total=("boardings_total", "sum"),
            alightings_total=("alightings_total", "sum"),
            trip_count=("trip_count", "sum"),
        )
        grouped["mean_load"] = grouped["mean_load"].round(2)
        return grouped
