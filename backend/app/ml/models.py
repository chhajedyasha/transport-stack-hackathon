"""ML Regressor models for passenger load forecasting and confidence intervals."""
from typing import Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import BaseEstimator, RegressorMixin


class HistoricalMeanRegressor(BaseEstimator, RegressorMixin):
    """Baseline Regressor (B1 & B2).

    Uses historical route-zone-hour median/mean where available (B1),
    falling back to network day-type hour mean (B2).
    """

    def __init__(self):
        self.route_zone_hour_means: Dict[tuple, float] = {}
        self.network_hour_means: Dict[tuple, float] = {}
        self.global_mean: float = 0.0

    def fit(self, df_train: pd.DataFrame, y=None) -> "HistoricalMeanRegressor":
        target = "mean_load"
        self.global_mean = float(df_train[target].mean()) if len(df_train) > 0 else 10.0
        
        # B1: (route_id, direction_id, zone_id, day_type, hour)
        rzh = df_train.groupby(["route_id", "direction_id", "zone_id", "day_type", "hour"])[target].mean().to_dict()
        self.route_zone_hour_means = {k: float(v) for k, v in rzh.items()}
        
        # B2: (day_type, hour)
        nh = df_train.groupby(["day_type", "hour"])[target].mean().to_dict()
        self.network_hour_means = {k: float(v) for k, v in nh.items()}
        
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in df.iterrows():
            r = row["route_id"]
            d = int(row["direction_id"])
            z = int(row["zone_id"])
            dt = str(row.get("day_type", "WEEKDAY"))
            h = int(row["hour"])
            
            key_b1 = (r, d, z, dt, h)
            key_b2 = (dt, h)
            
            if key_b1 in self.route_zone_hour_means:
                preds.append(self.route_zone_hour_means[key_b1])
            elif key_b2 in self.network_hour_means:
                preds.append(self.network_hour_means[key_b2])
            else:
                preds.append(self.global_mean)
                
        return np.array(preds, dtype=float)


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
