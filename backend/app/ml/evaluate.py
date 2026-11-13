"""Evaluation metrics and Relative Crowding Index (RCI) calibration."""
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score, accuracy_score


class RCICalibrator:
    """Calibrates continuous load-per-trip predictions into Relative Crowding Index (0-100)
    and categories (Low, Moderate, High / Seats Available, Standing Room, Crowded).
    """

    def __init__(
        self,
        rated_capacity: float = 60.0,
        mode: str = "capacity",
        percentiles: Optional[np.ndarray] = None,
    ):
        self.rated_capacity = float(rated_capacity)
        self.mode = mode
        self.percentiles = percentiles  # 101 thresholds for 0..100 percentiles

    def fit(self, y_train: np.ndarray) -> "RCICalibrator":
        """Calculates 101 percentile cutoffs from the training load distribution."""
        clean_y = np.maximum(0.0, y_train[~np.isnan(y_train)])
        self.percentiles = np.percentile(clean_y, np.linspace(0, 100, 101))
        # Ensure monotonically non-decreasing
        self.percentiles = np.maximum.accumulate(self.percentiles)
        return self

    def compute_rci(self, y: np.ndarray) -> np.ndarray:
        """Maps predicted loads to RCI (0-100)."""
        y_arr = np.nan_to_num(np.asarray(y, dtype=float), nan=0.0, posinf=60.0, neginf=0.0)
        y_arr = np.maximum(0.0, y_arr)

        if self.mode == "capacity":
            rci = (y_arr / self.rated_capacity) * 100.0
            return np.clip(np.round(rci, 2), 0.0, 100.0)
        else:
            if self.percentiles is None:
                raise RuntimeError("Calibrator not fitted for percentile mode.")
            rci = np.searchsorted(self.percentiles, y_arr, side="right") - 1
            return np.clip(rci, 0, 100).astype(float)

    def to_category(self, rci_values: np.ndarray, style: str = "standard") -> List[str]:
        """Categorizes RCI into official categories.
        style="standard" -> ["Low", "Moderate", "High"]
        style="descriptive" -> ["Seats Available", "Standing Room", "Crowded"]
        """
        cats = []
        for rci in rci_values:
            if rci < 40.0:
                cats.append("Low" if style == "standard" else "Seats Available")
            elif rci < 75.0:
                cats.append("Moderate" if style == "standard" else "Standing Room")
            else:
                cats.append("High" if style == "standard" else "Crowded")
        return cats

    def to_label(self, rci_values: np.ndarray) -> List[str]:
        """Maps RCI to commuter-facing descriptive labels."""
        return self.to_category(rci_values, style="descriptive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rated_capacity": self.rated_capacity,
            "mode": self.mode,
            "percentiles": self.percentiles.tolist() if self.percentiles is not None else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RCICalibrator":
        pct = np.array(data.get("percentiles", [])) if data.get("percentiles") else None
        return cls(
            rated_capacity=float(data.get("rated_capacity", 60.0)),
            mode=str(data.get("mode", "capacity")),
            percentiles=pct,
        )


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    calibrator: RCICalibrator,
    hours: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Computes full regression, ranking, and categorical metrics."""
    y_true = np.nan_to_num(np.asarray(y_true, dtype=float), nan=0.0)
    y_pred = np.maximum(0.0, np.nan_to_num(np.asarray(y_pred, dtype=float), nan=0.0))
    
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    sum_true = float(np.sum(y_true))
    wape = float(np.sum(np.abs(y_true - y_pred)) / sum_true) if sum_true > 0 else 0.0
    wape_percent = wape * 100.0
    
    # Global Spearman rank correlation
    if len(y_true) > 1 and np.std(y_pred) > 1e-6 and np.std(y_true) > 1e-6:
        spearman_corr, _ = spearmanr(y_true, y_pred)
        spearman_val = float(spearman_corr) if not np.isnan(spearman_corr) else 0.0
    else:
        spearman_val = 0.0
        
    # Categorical evaluation
    true_rci = calibrator.compute_rci(y_true)
    pred_rci = calibrator.compute_rci(y_pred)
    
    true_cats = calibrator.to_category(true_rci)
    pred_cats = calibrator.to_category(pred_rci)
    
    acc = float(accuracy_score(true_cats, pred_cats))
    macro_f1 = float(f1_score(true_cats, pred_cats, average="macro", zero_division=0))
    
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "wape": round(wape, 4),
        "wape_percent": round(wape_percent, 2),
        "spearman_rank_correlation": round(spearman_val, 4),
        "category_accuracy": round(acc, 4),
        "category_macro_f1": round(macro_f1, 4),
        "n_samples": int(len(y_true)),
    }

