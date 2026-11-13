"""crowdwise/backend/app/services/stop_search_service.py
Spatial aggregation and multi-modal stop discovery engine for Delhi NCT transit.

Features:
- F04: Contiguous 8-Zone Sequence Partitioning: zeta(s, N) = min(7, floor(8s / N)).
- F05: Multi-Modal Stop Search:
  1. Exact stop code and stop name lookups.
  2. Prefix matching for autocomplete.
  3. Accelerated inverted trigram index + Levenshtein fuzzy matching (threshold >= 0.45).
  4. Coordinate-based spatial search using scipy.spatial.cKDTree (<0.2ms query latency)
     with fine spherical Haversine re-ranking.
"""
import math
import logging
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple, Set
import numpy as np
from scipy.spatial import cKDTree

logger = logging.getLogger("crowdwise.stop_search_service")

# WGS-84 volumetric mean Earth radius in km
R_EARTH_KM = 6371.0088

# Delhi NCT geographic centroid for equirectangular planar projection
DELHI_LAT_DEG = 28.6139
DELHI_LON_DEG = 77.2090
DELHI_LAT_RAD = math.radians(DELHI_LAT_DEG)
DELHI_LON_RAD = math.radians(DELHI_LON_DEG)


# ---------------------------------------------------------------------------
# Feature F04: Contiguous 8-Zone Sequence Partitioner
# ---------------------------------------------------------------------------

class ZonePartitioner:
    """Partitions ordered stops of any route pattern into up to 8 contiguous zones."""

    MAX_ZONES: int = 8

    @classmethod
    def assign_stop_zone(cls, stop_sequence: int, total_stops: int) -> int:
        """Assigns a single stop sequence to a zone index [0..7].

        Closed-form formula:
            zeta(s, N) = s if N <= 8 else min(7, floor(8 * s / N))

        Args:
            stop_sequence: 0-indexed position of the stop along the pattern.
            total_stops: Total number of stops N in the pattern.

        Returns:
            Integer zone_id in range [0..min(7, total_stops - 1)].

        Raises:
            ValueError: If total_stops <= 0.
            IndexError: If stop_sequence < 0 or stop_sequence >= total_stops.
        """
        if total_stops <= 0:
            raise ValueError(f"total_stops must be positive, got {total_stops}")
        if not (0 <= stop_sequence < total_stops):
            raise IndexError(
                f"stop_sequence {stop_sequence} out of bounds for total_stops {total_stops}"
            )

        if total_stops <= cls.MAX_ZONES:
            return stop_sequence

        zone_id = min(cls.MAX_ZONES - 1, (stop_sequence * cls.MAX_ZONES) // total_stops)
        return int(zone_id)

    @classmethod
    def partition_pattern_stops(cls, stop_sequences: List[int]) -> Dict[int, int]:
        """Maps an ordered list of stop sequence numbers to zone IDs (0..7).

        Handles non-consecutive or 1-indexed sequences by ranking them first.

        Args:
            stop_sequences: List of raw stop sequences from GTFS.

        Returns:
            Dictionary mapping raw stop_sequence -> zone_id (0..7).
        """
        if not stop_sequences:
            return {}

        sorted_seqs = sorted(stop_sequences)
        N = len(sorted_seqs)

        result: Dict[int, int] = {}
        for rank, raw_seq in enumerate(sorted_seqs):
            zone_id = cls.assign_stop_zone(rank, N)
            result[raw_seq] = zone_id

        return result

    @classmethod
    def compute_zone_corridor_summary(
        cls,
        pattern_stops: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Computes zone bounding boxes, centroids, and terminal stops for UI display.

        Args:
            pattern_stops: List of stop dicts with keys:
                'stop_id', 'stop_name', 'stop_sequence', 'zone_id',
                'stop_lat', 'stop_lon', 'cum_dist_km'

        Returns:
            List of up to 8 zone summary objects.
        """
        if not pattern_stops:
            return []

        zones: Dict[int, Dict[str, Any]] = {}
        for s in pattern_stops:
            z = s["zone_id"]
            if z not in zones:
                zones[z] = {
                    "zone_id": z,
                    "stops": [],
                    "start_stop_id": s["stop_id"],
                    "start_stop_name": s.get("stop_name", ""),
                    "start_dist_km": s.get("cum_dist_km", 0.0),
                    "lats": [],
                    "lons": [],
                }
            zones[z]["stops"].append(s)
            zones[z]["lats"].append(s["stop_lat"])
            zones[z]["lons"].append(s["stop_lon"])
            zones[z]["end_stop_id"] = s["stop_id"]
            zones[z]["end_stop_name"] = s.get("stop_name", "")
            zones[z]["end_dist_km"] = s.get("cum_dist_km", 0.0)

        summary = []
        for z in sorted(zones.keys()):
            data = zones[z]
            stop_count = len(data["stops"])
            summary.append({
                "zone_id": z,
                "stop_count": stop_count,
                "start_stop_id": data["start_stop_id"],
                "start_stop_name": data["start_stop_name"],
                "end_stop_id": data["end_stop_id"],
                "end_stop_name": data["end_stop_name"],
                "start_dist_km": round(data["start_dist_km"], 2),
                "end_dist_km": round(data["end_dist_km"], 2),
                "zone_dist_km": round(max(0.0, data["end_dist_km"] - data["start_dist_km"]), 2),
                "centroid_lat": round(sum(data["lats"]) / stop_count, 6),
                "centroid_lon": round(sum(data["lons"]) / stop_count, 6),
                "bbox": [
                    min(data["lats"]), min(data["lons"]),
                    max(data["lats"]), max(data["lons"]),
                ],
            })

        return summary


# ---------------------------------------------------------------------------
# Feature F05: Multi-Modal Stop Search Engine
# ---------------------------------------------------------------------------

def _get_trigrams(text: str) -> Set[str]:
    """Generates padded 3-gram character shingles from string."""
    s = f"  {text.lower().strip()}  "
    if len(s) < 3:
        return {s}
    return {s[i:i + 3] for i in range(len(s) - 2)}


def _levenshtein_ratio(s1: str, s2: str) -> float:
    """Computes normalized Levenshtein similarity ratio [0.0..1.0]."""
    if s1 == s2:
        return 1.0
    m, n = len(s1), len(s2)
    if m == 0 or n == 0:
        return 0.0

    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        c1 = s1[i - 1]
        for j in range(1, n + 1):
            temp = dp[j]
            if c1 == s2[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp

    dist = dp[n]
    return max(0.0, 1.0 - (dist / max(m, n)))


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes accurate great-circle distance between two GPS coordinates in km."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return R_EARTH_KM * c


class StopSearchEngine:
    """In-memory multi-modal search engine indexing physical bus stops."""

    def __init__(self, stops: List[Dict[str, Any]]):
        """Initializes exact, fuzzy inverted trigram, and spatial cKDTree structures.

        Args:
            stops: List of stop dicts with keys:
                   'stop_id', 'stop_code', 'stop_name', 'stop_lat', 'stop_lon', 'is_terminal'
        """
        self.stops = stops
        self.N = len(stops)
        self.stop_by_id = {str(s["stop_id"]): s for s in stops}

        # Exact lookup dictionaries
        self.by_code: Dict[str, int] = {}
        self.by_exact_name: Dict[str, List[int]] = defaultdict(list)

        # Trigram structures
        self.stop_trigrams: List[Set[str]] = []
        self.inverted_trigrams: Dict[str, Set[int]] = defaultdict(set)

        for idx, s in enumerate(stops):
            code = str(s.get("stop_code", "")).strip().upper()
            if code:
                self.by_code[code] = idx

            name = str(s.get("stop_name", "")).strip().lower()
            if name:
                self.by_exact_name[name].append(idx)

            tris = _get_trigrams(name)
            self.stop_trigrams.append(tris)
            for tri in tris:
                self.inverted_trigrams[tri].add(idx)

        # Modality 3: Equirectangular cKDTree Spatial Index
        if self.N > 0:
            lats = np.array([math.radians(float(s["stop_lat"])) for s in stops], dtype=np.float64)
            lons = np.array([math.radians(float(s["stop_lon"])) for s in stops], dtype=np.float64)
            self.x = R_EARTH_KM * (lons - DELHI_LON_RAD) * math.cos(DELHI_LAT_RAD)
            self.y = R_EARTH_KM * (lats - DELHI_LAT_RAD)
            self.coords = np.column_stack((self.x, self.y))
            self.kdtree = cKDTree(self.coords)
        else:
            self.kdtree = None

    def search_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Executes combined exact, prefix, and accelerated fuzzy text search.

        Args:
            query: User search string.
            limit: Maximum stops to return.

        Returns:
            List of matching stop dictionaries with 'match_type', 'match_score', and 'distance_km'.
        """
        q = str(query).strip()
        if not q:
            return []

        q_lower = q.lower()
        q_upper = q.upper()

        matched_indices: Dict[int, Tuple[float, str]] = {}  # idx -> (score, match_type)

        # 1. Exact stop code match
        if q_upper in self.by_code:
            idx = self.by_code[q_upper]
            matched_indices[idx] = (1.00, "exact_code")

        # 2. Exact stop name match
        if q_lower in self.by_exact_name:
            for idx in self.by_exact_name[q_lower]:
                matched_indices[idx] = (0.95, "exact_name")

        # 3. Prefix match across stops
        for idx, stop in enumerate(self.stops):
            name_lower = str(stop.get("stop_name", "")).lower()
            code_upper = str(stop.get("stop_code", "")).upper()
            if code_upper.startswith(q_upper) and idx not in matched_indices:
                matched_indices[idx] = (0.85, "prefix_code")
            elif name_lower.startswith(q_lower) and idx not in matched_indices:
                matched_indices[idx] = (0.80, "prefix_name")

        # 4. Inverted Trigram + Levenshtein Fuzzy Search
        q_tris = _get_trigrams(q)
        if q_tris:
            candidate_counts: Dict[int, int] = defaultdict(int)
            for tri in q_tris:
                for idx in self.inverted_trigrams.get(tri, ()):
                    candidate_counts[idx] += 1

            min_shared = max(1, int(0.20 * len(q_tris)))
            for idx, shared_count in candidate_counts.items():
                if idx in matched_indices:
                    continue  # Already matched via exact/prefix
                if shared_count >= min_shared:
                    name_lower = str(self.stops[idx]["stop_name"]).lower()
                    denom = len(q_tris) + len(self.stop_trigrams[idx])
                    s_tri = (2.0 * shared_count) / max(1, denom)
                    if s_tri >= 0.20:
                        s_lev = _levenshtein_ratio(q_lower, name_lower)
                        is_pfx = 1.0 if name_lower.startswith(q_lower) else 0.0
                        composite = (0.50 * s_tri) + (0.50 * s_lev) + (0.15 * is_pfx)
                        if composite >= 0.45:
                            matched_indices[idx] = (round(composite, 3), "fuzzy")

        # Compile and sort results
        scored_results = []
        for idx, (score, m_type) in matched_indices.items():
            stop = self.stops[idx]
            scored_results.append({
                **stop,
                "match_type": m_type,
                "match_score": score,
                "distance_km": None,
            })

        # Sort: score DESC, is_terminal DESC, name length ASC
        scored_results.sort(
            key=lambda x: (
                -x["match_score"],
                -int(x.get("is_terminal", False)),
                len(str(x.get("stop_name", ""))),
            )
        )
        return scored_results[:limit]

    def search_nearest(
        self,
        lat: float,
        lon: float,
        radius_km: float = 2.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Queries spatial nearest stops within radius_km using cKDTree (<0.2ms latency).

        Args:
            lat: Query latitude.
            lon: Query longitude.
            radius_km: Search radius in km (default 2.0, max 25.0).
            limit: Maximum stops to return.

        Returns:
            List of stops sorted by distance_km ascending.
        """
        if self.kdtree is None or self.N == 0:
            return []

        # Validate coordinates roughly within Delhi NCR expanded bounds
        if not (27.0 <= lat <= 30.5 and 75.5 <= lon <= 78.5):
            return []

        radius_km = min(25.0, max(0.05, float(radius_km)))

        # Project query to planar coords
        q_lat_rad = math.radians(lat)
        q_lon_rad = math.radians(lon)
        qx = R_EARTH_KM * (q_lon_rad - DELHI_LON_RAD) * math.cos(DELHI_LAT_RAD)
        qy = R_EARTH_KM * (q_lat_rad - DELHI_LAT_RAD)

        # cKDTree sub-millisecond ball query
        indices = self.kdtree.query_ball_point([qx, qy], r=radius_km)
        if not indices:
            return []

        candidates = []
        for idx in indices:
            stop = self.stops[idx]
            dist = haversine_distance_km(lat, lon, float(stop["stop_lat"]), float(stop["stop_lon"]))
            if dist <= radius_km:
                candidates.append({
                    **stop,
                    "distance_km": round(dist, 3),
                    "match_type": "spatial",
                    "match_score": round(max(0.0, 1.0 - (dist / radius_km)), 3),
                })

        candidates.sort(key=lambda s: s["distance_km"])
        return candidates[:limit]

    def search(
        self,
        q: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: float = 2.0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Unified multi-modal stop search query entry point."""
        if lat is not None and lon is not None:
            return self.search_nearest(lat, lon, radius_km=radius_km, limit=limit)
        elif q:
            return self.search_text(q, limit=limit)
        return []
