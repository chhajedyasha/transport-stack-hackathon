"""Feature engineering pipeline for bus crowdedness estimation.
Strictly leakage-safe: all historical target aggregations are derived solely from the training partition.
"""
import math
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "direction_id",
    "zone_id",
    "position_fraction",
    "hour",
    "hour_sin",
    "hour_cos",
    "day_of_week",
    "is_weekend",
    "is_am_peak",
    "is_pm_peak",
    "is_midday",
    "is_night",
    "hist_route_zone_hour_mean",
    "hist_route_zone_mean",
    "hist_network_hour_mean",
    "has_history",
]


class FeaturePipeline:
    """Extracts features for training and serving without data leakage."""

    def __init__(self):
        self.route_zone_hour_stats: Dict[tuple, float] = {}
        self.route_zone_stats: Dict[tuple, float] = {}
        self.network_hour_stats: Dict[tuple, float] = {}
        self.global_mean: float = 0.0
        self.is_fitted: bool = False

    def fit(self, df_train: pd.DataFrame) -> "FeaturePipeline":
        """Fits historical aggregate lookups using the training partition ONLY."""
        df = df_train.copy()
        target = "mean_load"
        
        self.global_mean = float(df[target].mean()) if len(df) > 0 else 10.0
        
        # Route x Direction x Zone x DayType x Hour
        rzh = df.groupby(["route_id", "direction_id", "zone_id", "day_type", "hour"])[target].mean().to_dict()
        self.route_zone_hour_stats = {k: float(v) for k, v in rzh.items()}
        
        # Route x Direction x Zone
        rz = df.groupby(["route_id", "direction_id", "zone_id"])[target].mean().to_dict()
        self.route_zone_stats = {k: float(v) for k, v in rz.items()}
        
        # Network x DayType x Hour
        nh = df.groupby(["day_type", "hour"])[target].mean().to_dict()
        self.network_hour_stats = {k: float(v) for k, v in nh.items()}
        
        self.is_fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms input DataFrame into model feature matrix."""
        if not self.is_fitted:
            raise RuntimeError("FeaturePipeline must be fitted before transforming data.")
            
        res = pd.DataFrame(index=df.index)
        
        # 1. Structural features
        res["direction_id"] = df["direction_id"].astype(int)
        res["zone_id"] = df["zone_id"].astype(int)
        res["position_fraction"] = df["zone_id"].astype(float) / 7.0
        
        # 2. Calendar features
        hour = df["hour"].astype(int)
        res["hour"] = hour
        res["hour_sin"] = np.sin(2.0 * math.pi * hour / 24.0)
        res["hour_cos"] = np.cos(2.0 * math.pi * hour / 24.0)
        
        # Extract date attributes if trip_date is present
        if "trip_date" in df.columns:
            dates = pd.to_datetime(df["trip_date"])
            res["day_of_week"] = dates.dt.dayofweek
            res["is_weekend"] = (dates.dt.dayofweek >= 5).astype(int)
        else:
            # Fallback from day_type
            day_type_col = df["day_type"] if "day_type" in df.columns else pd.Series(["WEEKDAY"] * len(df), index=df.index)
            res["is_weekend"] = (day_type_col != "WEEKDAY").astype(int)
            res["day_of_week"] = np.where(res["is_weekend"] == 1, 5, 2)
            
        res["is_am_peak"] = ((hour >= 7) & (hour <= 10)).astype(int)
        res["is_pm_peak"] = ((hour >= 17) & (hour <= 20)).astype(int)
        res["is_midday"] = ((hour >= 11) & (hour <= 15)).astype(int)
        res["is_night"] = ((hour >= 22) | (hour <= 5)).astype(int)
        
        # 3. Leakage-safe historical lookups
        hist_rzh = []
        hist_rz = []
        hist_nh = []
        has_hist = []
        
        for idx, row in df.iterrows():
            r = row["route_id"]
            d = int(row["direction_id"])
            z = int(row["zone_id"])
            dt = str(row.get("day_type", "WEEKDAY"))
            h = int(row["hour"])
            
            # Network fallback
            nh_val = self.network_hour_stats.get((dt, h), self.global_mean)
            hist_nh.append(nh_val)
            
            # Route-zone fallback
            rz_val = self.route_zone_stats.get((r, d, z), nh_val)
            hist_rz.append(rz_val)
            
            # Specific route-zone-hour
            key_rzh = (r, d, z, dt, h)
            if key_rzh in self.route_zone_hour_stats:
                hist_rzh.append(self.route_zone_hour_stats[key_rzh])
                has_hist.append(1)
            else:
                hist_rzh.append(rz_val)
                has_hist.append(0)
                
        res["hist_route_zone_hour_mean"] = hist_rzh
        res["hist_route_zone_mean"] = hist_rz
        res["hist_network_hour_mean"] = hist_nh
        res["has_history"] = has_hist
        
        return res[FEATURE_COLUMNS]

    def transform_single(
        self,
        route_id: str,
        direction_id: int,
        zone_id: int,
        day_type: str,
        hour: int,
    ) -> np.ndarray:
        """Fast path transformation for a single prediction row."""
        df_single = pd.DataFrame([{
            "route_id": route_id,
            "direction_id": direction_id,
            "zone_id": zone_id,
            "day_type": day_type,
            "hour": hour,
        }])
        transformed = self.transform(df_single)
        return transformed.values
