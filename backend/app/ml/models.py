"""ML Regressor models for passenger load forecasting and confidence intervals."""
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import BaseEstimator, RegressorMixin


class HistoricalMeanRegressor(BaseEstimator, RegressorMixin):
    """Baseline Regressor with 6-level stratified fallback hierarchy.

    Hierarchy:
    Level 0: (route_id, direction_id, zone_id, day_type, hour)
    Level 1: (route_id, direction_id, zone_id, hour)
    Level 2: (route_id, zone_id, hour)
    Level 3: (route_id, hour)
    Level 4: network (day_type, hour)
    Level 5: global network (hour)
    Level 6: global mean
    """

    def __init__(self):
        self.route_dir_zone_dt_hour_means: Dict[tuple, float] = {}
        self.route_dir_zone_hour_means: Dict[tuple, float] = {}
        self.route_zone_hour_means_l2: Dict[tuple, float] = {}
        self.route_hour_means: Dict[tuple, float] = {}
        self.day_type_hour_means: Dict[tuple, float] = {}
        self.global_hour_means: Dict[int, float] = {}
        self.global_mean: float = 0.0
        # Backward-compatible aliases
        self.route_zone_hour_means: Dict[tuple, float] = {}
        self.network_hour_means: Dict[tuple, float] = {}

    def fit(self, df_train: pd.DataFrame, y=None) -> "HistoricalMeanRegressor":
        df = df_train.copy()
        target = "mean_load" if "mean_load" in df.columns else ("load" if "load" in df.columns else df.columns[-1])
        
        # Clean target: coerce numeric and drop NaNs (equivalent to np.nanmean)
        df[target] = pd.to_numeric(df[target], errors="coerce")
        df = df.dropna(subset=[target]).copy()

        # Map public holidays to SUNDAY baseline
        if "day_type" in df.columns:
            df["day_type"] = df["day_type"].replace({"HOLIDAY": "SUNDAY"})

        self.global_mean = float(df[target].mean()) if len(df) > 0 else 10.0

        # Level 0: (route_id, direction_id, zone_id, day_type, hour)
        rzdth = df.groupby(["route_id", "direction_id", "zone_id", "day_type", "hour"])[target].mean().to_dict()
        self.route_dir_zone_dt_hour_means = {k: float(v) for k, v in rzdth.items()}
        self.route_zone_hour_means = self.route_dir_zone_dt_hour_means

        # Level 1: (route_id, direction_id, zone_id, hour)
        rdzh = df.groupby(["route_id", "direction_id", "zone_id", "hour"])[target].mean().to_dict()
        self.route_dir_zone_hour_means = {k: float(v) for k, v in rdzh.items()}

        # Level 2: (route_id, zone_id, hour)
        rzh = df.groupby(["route_id", "zone_id", "hour"])[target].mean().to_dict()
        self.route_zone_hour_means_l2 = {k: float(v) for k, v in rzh.items()}

        # Level 3: (route_id, hour)
        rh = df.groupby(["route_id", "hour"])[target].mean().to_dict()
        self.route_hour_means = {k: float(v) for k, v in rh.items()}

        # Level 4: (day_type, hour)
        dth = df.groupby(["day_type", "hour"])[target].mean().to_dict()
        self.day_type_hour_means = {k: float(v) for k, v in dth.items()}
        self.network_hour_means = self.day_type_hour_means

        # Level 5: (hour)
        h_means = df.groupby("hour")[target].mean().to_dict()
        self.global_hour_means = {k: float(v) for k, v in h_means.items()}

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        r_vals = df["route_id"].astype(str).values
        d_vals = df["direction_id"].astype(int).values
        z_vals = df["zone_id"].astype(int).values
        dt_vals = df["day_type"].astype(str).values if "day_type" in df.columns else np.array(["WEEKDAY"] * len(df))
        h_vals = df["hour"].astype(int).values

        preds = []
        for r, d, z, dt, h in zip(r_vals, d_vals, z_vals, dt_vals, h_vals):
            preds.append(self.predict_single(r, d, z, dt, h))

        return np.maximum(0.0, np.array(preds, dtype=float))

    def predict_single(
        self,
        route_id: str,
        direction_id: int,
        zone_id: int,
        day_type: str,
        hour: int,
    ) -> float:
        """Evaluates single-cell prediction across complete 6-level fallback hierarchy."""
        dt_norm = "SUNDAY" if day_type == "HOLIDAY" else str(day_type)
        r = str(route_id)
        d = int(direction_id)
        z = int(zone_id)
        h = int(hour)

        # Level 0: (route, dir, zone, day_type, hour)
        if (r, d, z, dt_norm, h) in self.route_dir_zone_dt_hour_means:
            return max(0.0, self.route_dir_zone_dt_hour_means[(r, d, z, dt_norm, h)])

        # Level 1: (route, dir, zone, hour)
        if (r, d, z, h) in self.route_dir_zone_hour_means:
            return max(0.0, self.route_dir_zone_hour_means[(r, d, z, h)])

        # Level 2: (route, zone, hour)
        if (r, z, h) in self.route_zone_hour_means_l2:
            return max(0.0, self.route_zone_hour_means_l2[(r, z, h)])

        # Level 3: (route, hour)
        if (r, h) in self.route_hour_means:
            return max(0.0, self.route_hour_means[(r, h)])

        # Level 4: (day_type, hour)
        if (dt_norm, h) in self.day_type_hour_means:
            return max(0.0, self.day_type_hour_means[(dt_norm, h)])

        # Level 5: (hour)
        if h in self.global_hour_means:
            return max(0.0, self.global_hour_means[h])

        # Level 6: global mean
        return max(0.0, self.global_mean)


class CrowdRandomForestRegressor:
    """Production Random Forest regressor with tree-variance confidence intervals."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: Optional[int] = 16,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        random_state: int = 42,
        n_jobs: int = -1,
    ):
        self.rf = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=n_jobs,
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> "CrowdRandomForestRegressor":
        self.rf.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
        preds = self.rf.predict(X)
        return np.maximum(0.0, preds)

    def predict_with_confidence(
        self,
        X: np.ndarray,
        has_history: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, list]:
        """Returns mean prediction, p10, p90 intervals, and confidence categorical ratings."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet.")
            
        # Collect predictions across individual estimators
        tree_preds = np.array([tree.predict(X) for tree in self.rf.estimators_])
        # tree_preds shape: (n_estimators, n_samples)
        
        mean_preds = np.maximum(0.0, np.mean(tree_preds, axis=0))
        p10 = np.maximum(0.0, np.percentile(tree_preds, 10, axis=0))
        p90 = np.maximum(0.0, np.percentile(tree_preds, 90, axis=0))
        
        spread = p90 - p10
        # Coefficient of variation or relative spread
        rel_spread = np.where(mean_preds > 0.1, spread / mean_preds, spread)
        
        confidence = []
        for i in range(len(mean_preds)):
            r_spr = rel_spread[i]
            hist_flag = has_history[i] if has_history is not None else 1
            
            if hist_flag == 0:
                confidence.append("low")
            elif r_spr < 0.35:
                confidence.append("high")
            elif r_spr < 0.75:
                confidence.append("medium")
            else:
                confidence.append("low")
                
        return mean_preds, p10, p90, confidence

