"""Evaluation metrics and Relative Crowding Index (RCI) percentile calibration."""
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import mean_absolute_error, mean_squared_error, f1_score, accuracy_score


class RCICalibrator:
    """Calibrates continuous load-per-trip predictions into Relative Crowding Index (0-100)
    and categories (Seats Available, Standing Room, Crowded).
    """

    def __init__(self, percentiles: Optional[np.ndarray] = None):
        self.percentiles = percentiles  # 101 thresholds for 0..100 percentiles

    def fit(self, y_train: np.ndarray) -> "RCICalibrator":
        """Calculates 101 percentile cutoffs from the training load distribution."""
        clean_y = np.maximum(0.0, y_train[~np.isnan(y_train)])
        self.percentiles = np.percentile(clean_y, np.linspace(0, 100, 101))
        # Ensure monotonically non-decreasing
        self.percentiles = np.maximum.accumulate(self.percentiles)
        return self

    def compute_rci(self, y: np.ndarray) -> np.ndarray:
        """Maps predicted loads to percentile rank (0-100)."""
        if self.percentiles is None:
            raise RuntimeError("Calibrator not fitted.")
            
        rci = np.searchsorted(self.percentiles, y, side="right") - 1
        return np.clip(rci, 0, 100).astype(float)

    def to_category(self, rci_values: np.ndarray) -> List[str]:
        """Categorizes RCI into official hackathon terminology."""
        cats = []
        for rci in rci_values:
            if rci < 40.0:
                cats.append("Seats Available")
            elif rci <= 75.0:
                cats.append("Standing Room")
            else:
                cats.append("Crowded")
        return cats

    def to_dict(self) -> Dict[str, Any]:
        return {"percentiles": self.percentiles.tolist() if self.percentiles is not None else []}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RCICalibrator":
        return cls(percentiles=np.array(data.get("percentiles", [])))


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    calibrator: RCICalibrator,
    hours: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """Computes full regression, ranking, and categorical metrics."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.maximum(0.0, np.asarray(y_pred, dtype=float))
    
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    sum_true = float(np.sum(y_true))
    wape = float(np.sum(np.abs(y_true - y_pred)) / sum_true) if sum_true > 0 else 0.0
    
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
        "spearman_rank_correlation": round(spearman_val, 4),
        "category_accuracy": round(acc, 4),
        "category_macro_f1": round(macro_f1, 4),
        "n_samples": int(len(y_true)),
    }
