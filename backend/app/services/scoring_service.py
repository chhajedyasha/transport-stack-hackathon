"""crowdwise/backend/app/services/scoring_service.py
Multi-Objective Preference Scoring Engine for CrowdWise (Feature F21).

Mathematical Formulation:
- Presets:
  - Fastest:       w_time = 1.0, w_crowd = 0.0, w_wait = 0.0
  - Balanced:      w_time = 0.5, w_crowd = 0.5, w_wait = 0.0
  - Least Crowded: w_time = 0.2, w_crowd = 0.8, w_wait = 0.0
- Journey Composite Crowding:
  C_journey = 0.40 * C_boarding + 0.60 * C_peak_leg
  where C_boarding is RCI at boarding zone, and C_peak_leg is max RCI across traversed zones.
- Benchmark Travel Time Normalization:
  T_bar = mean(T_total) across candidate routes (safe floor: max(T_bar, 1.0)).
  When all candidate routes have identical travel time, T_bar = T_total, avoiding division skew.
- Normalization Score:
  S = w_time * (T_total / T_bar) + w_crowd * (C_journey / 100.0) + w_wait * (T_wait / T_bar)
  (lower score ranks first).
- Detour Constraint (Least Crowded preset):
  T_total <= 1.6 * min(T_total) to avoid excessive detours for marginal crowding gains.
- Commuter UX Labels & Technical Categories:
  - RCI < 40.0:         Category "Low",      Label "Seats Available" (Green)
  - 40.0 <= RCI < 75.0: Category "Moderate", Label "Standing Room"   (Amber)
  - RCI >= 75.0:        Category "High",     Label "Crowded"         (Red)
"""
import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


PRESET_WEIGHTS: Dict[str, Dict[str, float]] = {
    "fastest": {
        "w_time": 1.0,
        "w_crowd": 0.0,
        "w_wait": 0.0,
    },
    "balanced": {
        "w_time": 0.5,
        "w_crowd": 0.5,
        "w_wait": 0.0,
    },
    "least_crowded": {
        "w_time": 0.2,
        "w_crowd": 0.8,
        "w_wait": 0.0,
    },
}

RCI_THRESHOLDS = {
    "low": 40.0,
    "high": 75.0,
}

COMMUTER_LABELS = {
    "low": "Seats Available",
    "moderate": "Standing Room",
    "high": "Crowded",
}

TECHNICAL_CATEGORIES = {
    "low": "Low",
    "moderate": "Moderate",
    "high": "High",
}


def rci_to_label(rci: float) -> str:
    """Maps RCI (0-100) to commuter-facing UX label."""
    r = float(rci)
    if r < RCI_THRESHOLDS["low"]:
        return COMMUTER_LABELS["low"]
    elif r < RCI_THRESHOLDS["high"]:
        return COMMUTER_LABELS["moderate"]
    return COMMUTER_LABELS["high"]


def rci_to_category(rci: float) -> str:
    """Maps RCI (0-100) to standard technical category."""
    r = float(rci)
    if r < RCI_THRESHOLDS["low"]:
        return TECHNICAL_CATEGORIES["low"]
    elif r < RCI_THRESHOLDS["high"]:
        return TECHNICAL_CATEGORIES["moderate"]
    return TECHNICAL_CATEGORIES["high"]


def compute_journey_crowding(boarding_rci: float, peak_rci: float) -> float:
    """Calculates composite journey crowding index:
    C_journey = 0.40 * C_boarding + 0.60 * C_peak_leg.
    Strictly bounded in [0.0, 100.0].
    """
    b = max(0.0, min(100.0, float(boarding_rci)))
    p = max(0.0, min(100.0, float(peak_rci)))
    # If peak is somehow less than boarding (e.g. data anomaly), peak is at least boarding
    p = max(b, p)
    c_journey = (0.40 * b) + (0.60 * p)
    return round(float(c_journey), 1)


def calculate_benchmark_time(candidates: List[Dict[str, Any]]) -> float:
    """Computes benchmark travel time T_bar across candidate routes.
    If all candidate routes have identical travel time, returns that travel time.
    Applies safe floor of 1.0 to prevent division by zero.
    """
    if not candidates:
        return 1.0
    times = []
    for c in candidates:
        if "timing" in c and "total_duration_min" in c["timing"]:
            times.append(float(c["timing"]["total_duration_min"]))
        elif "total_time_min" in c:
            times.append(float(c["total_time_min"]))
    if not times:
        return 1.0
    if len(times) == 1:
        return max(1.0, times[0])
    # Check if all candidate routes have identical travel time within floating precision
    if max(times) - min(times) < 1e-4:
        return max(1.0, times[0])
    mean_t = sum(times) / len(times)
    return max(1.0, mean_t)


def infer_departure_context(
    departure_time: Optional[str] = None,
    day_type: Optional[str] = None,
) -> Tuple[int, str]:
    """Infers departure hour (0-23) and canonical day_type (WEEKDAY, SATURDAY, SUNDAY)
    from ISO-8601 departure timestamp or HH:MM:SS string and explicit day_type parameter.
    """
    resolved_day_type = "WEEKDAY"
    hour = 18

    if departure_time:
        dep_str = str(departure_time).strip()
        try:
            # Handle ISO timestamp e.g. '2026-10-14T18:00:00Z'
            dt = datetime.fromisoformat(dep_str.replace("Z", "+00:00"))
            hour = dt.hour
            weekday_idx = dt.weekday()  # Mon=0, ..., Fri=4, Sat=5, Sun=6
            if weekday_idx < 5:
                resolved_day_type = "WEEKDAY"
            elif weekday_idx == 5:
                resolved_day_type = "SATURDAY"
            else:
                resolved_day_type = "SUNDAY"
        except Exception:
            # Try HH:MM:SS format
            try:
                parts = dep_str.split(":")
                hour = int(parts[0]) % 24
            except Exception:
                hour = 18

    # Explicit day_type override if provided and valid
    if day_type:
        dt_upper = str(day_type).strip().upper()
        if dt_upper in {"WEEKDAY", "SATURDAY", "SUNDAY"}:
            resolved_day_type = dt_upper
        elif dt_upper == "HOLIDAY":
            resolved_day_type = "SUNDAY"  # GTFS convention: public holidays run Sunday schedules

    return hour, resolved_day_type


def aggregate_journey_confidence(confidences: List[str]) -> str:
    """Aggregates zone-level confidences into a conservative journey confidence."""
    if not confidences:
        return "medium"
    cleaned = [str(c).lower() for c in confidences]
    if "low" in cleaned:
        return "low"
    if "medium" in cleaned:
        return "medium"
    return "high"


def generate_recommendation_reason(
    candidate: Dict[str, Any],
    preference: str,
    fastest_time: float,
    is_top: bool = False,
) -> str:
    """Generates commuter-facing transparent explanation of the recommendation."""
    t_total = float(candidate["timing"].get("total_duration_min", candidate.get("total_time_min", 40.0)))
    c_journey = float(candidate["crowding"].get("journey_rci", candidate.get("rci", 50.0)))
    category = candidate["crowding"].get("label", candidate["crowding"].get("category", candidate.get("crowding_category", "Standing Room")))
    
    if preference == "fastest":
        if is_top or abs(t_total - fastest_time) < 0.1:
            return f"Fastest transit duration: {t_total:.0f} mins total (minimal travel & wait time)"
        diff = t_total - fastest_time
        return f"{t_total:.0f} mins total (+{diff:.0f} mins vs fastest) — {category}"
        
    elif preference == "least_crowded":
        if is_top:
            diff = t_total - fastest_time
            if diff > 1.0:
                return f"Lowest crowd index ({c_journey:.0f}/100) — {category} (+{diff:.0f} mins vs fastest)"
            return f"Lowest crowd index ({c_journey:.0f}/100) — {category} with fastest time!"
        return f"Crowd index: {c_journey:.0f}/100 — {category} ({t_total:.0f} mins total)"
        
    else:  # balanced
        if is_top:
            return f"Balanced trade-off: {t_total:.0f} mins with {category} ({c_journey:.0f}/100 RCI)"
        return f"Alternative option: {t_total:.0f} mins — {category} ({c_journey:.0f}/100 RCI)"


class MultiObjectiveScorer:
    """Scores, ranks, and annotates journey options using multi-objective preference presets."""

    def __init__(self, preset_weights: Optional[Dict[str, Dict[str, float]]] = None):
        self.preset_weights = preset_weights or PRESET_WEIGHTS

    def score_candidates(
        self,
        candidates: List[Dict[str, Any]],
        preference: str = "balanced",
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """Scores and ranks journey candidates according to multi-objective preference presets.
        
        Formula:
          S = w_time * (T_total / T_bar) + w_crowd * (C_journey / 100.0) + w_wait * (T_wait / T_bar)
        
        Tie-breaking:
          1. Lowest score S
          2. Secondary preference intent (T_total for fastest/balanced, C_journey for least_crowded)
          3. Lowest wait time T_wait
          4. Deterministic route_id / pattern_id
        """
        if not candidates:
            return []

        pref_key = str(preference).strip().lower().replace(" ", "_").replace("-", "_")
        weights = custom_weights or self.preset_weights.get(pref_key, self.preset_weights["balanced"])
        w_time = float(weights.get("w_time", 0.5))
        w_crowd = float(weights.get("w_crowd", 0.5))
        w_wait = float(weights.get("w_wait", 0.0))

        # 1. Benchmark travel time across candidate routes
        t_bar = calculate_benchmark_time(candidates)
        fastest_time = min(float(c["timing"].get("total_duration_min", c.get("total_time_min", 1.0))) for c in candidates)

        # 2. In least_crowded preset, prune excessive detours: T_total <= 1.6 * min(T_total)
        filtered = candidates
        if pref_key == "least_crowded":
            max_allowed = 1.60 * fastest_time
            constrained = [c for c in candidates if float(c["timing"].get("total_duration_min", c.get("total_time_min", 0.0))) <= max_allowed]
            # Fallback to avoid empty option set if constraint was overly restrictive
            if constrained:
                filtered = constrained

        # 3. Compute score and enrich crowding fields for each candidate
        for c in filtered:
            t_total = float(c["timing"].get("total_duration_min", c.get("total_time_min", 40.0)))
            t_wait = float(c["timing"].get("wait_time_min", c.get("wait_time_min", 5.0)))
            
            # Ensure C_journey is populated
            crowd = c.get("crowding", {})
            boarding_rci = float(crowd.get("boarding_rci", crowd.get("peak_rci", c.get("rci", 40.0))))
            peak_rci = float(crowd.get("peak_rci", boarding_rci))
            c_journey = compute_journey_crowding(boarding_rci, peak_rci)
            
            crowd["boarding_rci"] = round(boarding_rci, 1)
            crowd["peak_rci"] = round(peak_rci, 1)
            crowd["journey_rci"] = round(c_journey, 1)
            
            # Populate commuter UX labels alongside technical categories
            journey_label = rci_to_label(c_journey)
            journey_category = rci_to_category(c_journey)
            crowd["label"] = journey_label
            crowd["crowding_label"] = journey_label
            crowd["category"] = journey_label  # Backward-compatible with existing test expectations
            crowd["technical_category"] = journey_category
            crowd["crowding_category"] = journey_category

            # Top-level synchronization for tests
            c["rci"] = round(c_journey, 1)
            c["crowding_category"] = journey_category
            c["crowding_label"] = journey_label

            # Normalization terms
            time_norm = t_total / t_bar
            crowd_norm = c_journey / 100.0
            wait_norm = t_wait / t_bar

            score = (w_time * time_norm) + (w_crowd * crowd_norm) + (w_wait * wait_norm)
            c["score"] = round(float(score), 4)
            c["composite_score"] = round(float(score), 4)

        # 4. Deterministic multi-tier sorting
        if pref_key == "fastest":
            filtered.sort(
                key=lambda x: (
                    x["score"],
                    float(x["timing"].get("total_duration_min", x.get("total_time_min", 0.0))),
                    float(x["crowding"].get("journey_rci", x.get("rci", 0.0))),
                    float(x["timing"].get("wait_time_min", x.get("wait_time_min", 0.0))),
                    str(x.get("route_id", "")),
                    str(x.get("pattern_id", "")),
                )
            )
        elif pref_key == "least_crowded":
            filtered.sort(
                key=lambda x: (
                    x["score"],
                    float(x["crowding"].get("journey_rci", x.get("rci", 0.0))),
                    float(x["crowding"].get("peak_rci", x.get("rci", 0.0))),
                    float(x["timing"].get("total_duration_min", x.get("total_time_min", 0.0))),
                    float(x["timing"].get("wait_time_min", x.get("wait_time_min", 0.0))),
                    str(x.get("route_id", "")),
                    str(x.get("pattern_id", "")),
                )
            )
        else:  # balanced
            filtered.sort(
                key=lambda x: (
                    x["score"],
                    float(x["timing"].get("total_duration_min", x.get("total_time_min", 0.0))),
                    float(x["crowding"].get("journey_rci", x.get("rci", 0.0))),
                    float(x["timing"].get("wait_time_min", x.get("wait_time_min", 0.0))),
                    str(x.get("route_id", "")),
                    str(x.get("pattern_id", "")),
                )
            )

        # 5. Flag recommended option and annotate recommendation reasons
        for idx, c in enumerate(filtered):
            is_top = (idx == 0)
            c["is_recommended"] = is_top
            rec_text = generate_recommendation_reason(
                candidate=c,
                preference=pref_key,
                fastest_time=fastest_time,
                is_top=is_top,
            )
            c["recommendation_reason"] = rec_text
            c["recommendation"] = rec_text

        return filtered
