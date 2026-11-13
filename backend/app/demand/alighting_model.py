"""crowdwise/backend/app/demand/alighting_model.py
Feature F08: Mode B Hybrid Reverse-Direction + Distance-Decay Alighting Inference Engine.
"""
import math
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np


class ModeBAlightingInferenceEngine:
    """F08: Probabilistic alighting inference engine fusing reverse commute flows with distance-decay gravity."""

    def __init__(
        self,
        lambda_decay: float = 0.15,
        decay_lambda: Optional[float] = None,
        alpha_cap: float = 0.75,
        m_threshold: float = 50.0,
        min_dist_threshold_km: float = 0.1,
    ):
        self.lambda_decay = decay_lambda if decay_lambda is not None else lambda_decay
        self.alpha_cap = alpha_cap
        self.m_threshold = m_threshold
        self.min_dist_threshold_km = min_dist_threshold_km

    def compute_alighting_probabilities(
        self,
        pattern_stops: List[Any],
        boarding_idx: int,
        reverse_boardings: Optional[Dict[int, int]] = None,
        stop_distances_km: Optional[Dict[int, float]] = None,
        alpha_override: Optional[float] = None,
    ) -> Dict[int, float]:
        """Adapter method computing downstream alighting probabilities given full pattern stops."""
        n = len(pattern_stops)
        downstream = list(range(boarding_idx + 1, n))
        dist_dict: Dict[int, float] = {}
        if stop_distances_km is None:
            for s in pattern_stops:
                seq = int(s[0]) if isinstance(s, (tuple, list)) else int(getattr(s, "stop_sequence", 0))
                dist = float(s[3]) if isinstance(s, (tuple, list)) and len(s) > 3 else float(getattr(s, "cum_dist_km", 0.0))
                dist_dict[seq] = dist
        else:
            dist_dict = stop_distances_km

        return self.compute_alighting_probability(
            boarding_seq=boarding_idx,
            downstream_seqs=downstream,
            reverse_boardings=reverse_boardings,
            stop_distances_km=dist_dict,
            alpha_override=alpha_override,
        )

    def compute_alighting_probability(
        self,
        boarding_seq: int,
        downstream_seqs: List[int],
        reverse_boardings: Optional[Dict[int, int]] = None,
        stop_distances_km: Optional[Dict[int, float]] = None,
        alpha_override: Optional[float] = None,
    ) -> Dict[int, float]:
        """Calculates P(alight at stop j | boarded at stop i) for all valid downstream stops.

        Args:
            boarding_seq: Origin stop sequence index i.
            downstream_seqs: List of candidate stop sequences.
            reverse_boardings: Historical boarding counts observed at matching physical stops in reverse direction.
            stop_distances_km: Cumulative distance along route pattern in kilometers.
            alpha_override: Optional explicit blending factor override [0.0, 1.0].

        Returns:
            Dictionary mapping downstream stop sequence j -> alighting probability P(j | i).
            Sum of probabilities across downstream stops equals 1.0.
        """
        valid_downstream = [j for j in downstream_seqs if j > boarding_seq]
        if not valid_downstream:
            return {}

        # Penultimate stop rule: single downstream stop -> probability = 1.0 unconditionally
        if len(valid_downstream) == 1:
            return {valid_downstream[0]: 1.0}

        rev_dict = reverse_boardings or {}
        dist_dict = stop_distances_km or {}

        # 1. Reverse-Direction Commute Model
        total_rev = sum(rev_dict.get(j, 0) for j in valid_downstream)
        if total_rev > 0:
            p_rev = {j: rev_dict.get(j, 0) / total_rev for j in valid_downstream}
            eff_alpha = (
                alpha_override
                if alpha_override is not None
                else min(self.alpha_cap, total_rev / self.m_threshold)
            )
        else:
            p_rev = {j: 0.0 for j in valid_downstream}
            eff_alpha = 0.0

        # 2. Distance-Decay Gravity Model
        origin_dist = dist_dict.get(boarding_seq, 0.0)
        decay_terms: Dict[int, float] = {}
        for j in valid_downstream:
            raw_delta = dist_dict.get(j, 1.0) - origin_dist
            delta_d = max(self.min_dist_threshold_km, raw_delta)
            decay_terms[j] = math.exp(-self.lambda_decay * delta_d)

        sum_decay = sum(decay_terms.values())
        if sum_decay > 0:
            p_decay = {j: decay_terms[j] / sum_decay for j in valid_downstream}
        else:
            p_decay = {j: 1.0 / len(valid_downstream) for j in valid_downstream}

        # 3. Hybrid Blend
        probs: Dict[int, float] = {}
        for j in valid_downstream:
            prob = eff_alpha * p_rev[j] + (1.0 - eff_alpha) * p_decay[j]
            probs[j] = round(prob, 6)

        # Normalize to ensure sum == 1.0
        tot = sum(probs.values())
        if tot > 0:
            probs = {k: round(v / tot, 6) for k, v in probs.items()}
        return probs

    def reconstruct_trip(
        self,
        pattern_stops: List[Any],
        boardings_by_seq: Dict[int, int],
        reverse_boardings: Optional[Dict[int, int]] = None,
        alpha_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Reconstructs alightings and on-board passenger loads along the route pattern.

        Args:
            pattern_stops: List of tuples (seq, stop_id, zone_id, cum_dist) or objects.
            boardings_by_seq: Dictionary mapping stop_seq -> passenger boardings.
            reverse_boardings: Dictionary mapping stop_seq -> reverse boardings.
            alpha_override: Optional blending weight override.

        Returns:
            Dict containing 'boardings', 'alightings', and 'loads' as lists.
        """
        n = len(pattern_stops)
        if n == 0:
            return {"boardings": [], "alightings": [], "loads": []}

        # Extract stop sequence to distance mapping
        stop_distances: Dict[int, float] = {}
        for s in pattern_stops:
            if isinstance(s, (tuple, list)):
                seq = int(s[0])
                dist = float(s[3]) if len(s) > 3 else float(seq)
            elif isinstance(s, dict):
                seq = int(s.get("stop_sequence", s.get("seq", 0)))
                dist = float(s.get("cum_dist_km", s.get("dist", seq)))
            else:
                seq = int(getattr(s, "stop_sequence", getattr(s, "seq", 0)))
                dist = float(getattr(s, "cum_dist_km", getattr(s, "dist", seq)))
            stop_distances[seq] = dist

        downstream_all = list(range(n))
        inferred_alightings = np.zeros(n, dtype=np.float64)
        boardings_array = np.zeros(n, dtype=np.float64)

        for s in range(n):
            b_s = float(boardings_by_seq.get(s, 0))
            boardings_array[s] = b_s
            if b_s > 0 and s < n - 1:
                probs = self.compute_alighting_probability(
                    boarding_seq=s,
                    downstream_seqs=downstream_all,
                    reverse_boardings=reverse_boardings or {},
                    stop_distances_km=stop_distances,
                    alpha_override=alpha_override,
                )
                for j, p in probs.items():
                    if j < n:
                        inferred_alightings[j] += b_s * p

        # Terminal Stop Conservation Clearance:
        # All remaining passengers on board MUST alight at the terminal stop n - 1
        alightings_before_terminus = float(np.sum(inferred_alightings[: n - 1]))
        total_boardings = float(np.sum(boardings_array))
        inferred_alightings[n - 1] = max(0.0, total_boardings - alightings_before_terminus)

        # Passenger Load Recurrence: L_0 = B_0, L_s = max(0, L_{s-1} + B_s - A_s)
        loads = np.zeros(n, dtype=np.float64)
        curr_load = 0.0
        for s in range(n):
            curr_load = curr_load + boardings_array[s] - inferred_alightings[s]
            loads[s] = max(0.0, curr_load)
        loads[n - 1] = 0.0  # Terminal stop strictly 0

        return {
            "boardings": boardings_array.tolist(),
            "alightings": inferred_alightings.tolist(),
            "loads": loads.tolist(),
        }
