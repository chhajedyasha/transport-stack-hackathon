"""Crowd Prediction Service wrapping trained ML artifacts and RCI mapping."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd

from app.ml.features import FeaturePipeline
from app.ml.evaluate import RCICalibrator

logger = logging.getLogger(__name__)

# Search paths for ML artifacts
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
if not MODELS_DIR.exists():
    MODELS_DIR = Path("models")


class MLService:
    """Singleton service for loading models and executing fast predictions."""

    _instance = None

    def __init__(self, models_dir: Path = MODELS_DIR):
        self.models_dir = Path(models_dir)
        self.rf_model = None
        self.baseline_model = None
        self.feature_pipeline: Optional[FeaturePipeline] = None
        self.calibrator: Optional[RCICalibrator] = None
        self.metadata: Dict[str, Any] = {}
        self.is_loaded = False
        self._load_artifacts()

    @classmethod
    def get_instance(cls) -> "MLService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_artifacts(self):
        """Loads trained model artifacts if present on disk."""
        rf_path = self.models_dir / "random_forest_regressor.pkl"
        pipe_path = self.models_dir / "feature_pipeline.pkl"
        calib_path = self.models_dir / "rci_calibrator.json"
        meta_path = self.models_dir / "metadata.json"
        
        if rf_path.exists() and pipe_path.exists():
            try:
                self.rf_model = joblib.load(rf_path)
                self.feature_pipeline = joblib.load(pipe_path)
                
                if calib_path.exists():
                    with open(calib_path, "r", encoding="utf-8") as f:
                        self.calibrator = RCICalibrator.from_dict(json.load(f))
                else:
                    self.calibrator = RCICalibrator(percentiles=np.linspace(0, 80, 101))
                    
                if meta_path.exists():
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                        
                self.is_loaded = True
                logger.info(f"MLService: Successfully loaded models from {self.models_dir}")
            except Exception as e:
                logger.warning(f"MLService: Error loading ML artifacts: {e}")
                self.is_loaded = False
        else:
            logger.info("MLService: No pre-trained artifacts found. Will use heuristic fallback.")
            self.is_loaded = False

    def predict_crowd(
        self,
        route_id: str,
        direction_id: int,
        zone_id: int,
        day_type: str = "WEEKDAY",
        hour: int = 18,
    ) -> Dict[str, Any]:
        """Returns estimated crowdedness, RCI, category and confidence for a route cell."""
        # 1. Fallback heuristic if models not loaded
        if not self.is_loaded or self.rf_model is None or self.feature_pipeline is None:
            # Domain-informed fallback heuristic
            is_peak = hour in [8, 9, 10, 17, 18, 19, 20]
            is_night = hour >= 22 or hour <= 5
            base_load = 38.0 if is_peak else (8.0 if is_night else 22.0)
            if day_type == "SUNDAY":
                base_load *= 0.75
            rci = min(100.0, max(0.0, (base_load / 60.0) * 100.0))
            category = "Crowded" if rci > 75.0 else ("Standing Room" if rci >= 40.0 else "Seats Available")
            
            return {
                "route_id": route_id,
                "direction_id": int(direction_id),
                "zone_id": int(zone_id),
                "day_type": day_type,
                "hour": int(hour),
                "load": round(base_load, 1),
                "rci": round(rci, 1),
                "category": category,
                "confidence": "low",
                "tier": "estimated",
                "model_version": "fallback_heuristic",
            }
            
        # 2. Production prediction via Random Forest
        X = self.feature_pipeline.transform_single(
            route_id=str(route_id),
            direction_id=int(direction_id),
            zone_id=int(zone_id),
            day_type=str(day_type),
            hour=int(hour),
        )
        
        has_hist = np.array([int(X[0, -1])])
        mean_preds, p10, p90, confidences = self.rf_model.predict_with_confidence(X, has_history=has_hist)
        
        pred_load = float(mean_preds[0])
        rci_val = float(self.calibrator.compute_rci(np.array([pred_load]))[0])
        category = self.calibrator.to_category(np.array([rci_val]))[0]
        confidence = confidences[0]
        
        return {
            "route_id": str(route_id),
            "direction_id": int(direction_id),
            "zone_id": int(zone_id),
            "day_type": str(day_type),
            "hour": int(hour),
            "load": round(pred_load, 1),
            "rci": round(rci_val, 1),
            "category": category,
            "confidence": confidence,
            "tier": "estimated",
            "interval": {
                "p10": round(float(p10[0]), 1),
                "p90": round(float(p90[0]), 1),
            },
            "model_version": self.metadata.get("version", "1.0.0"),
        }

    def predict_journey_zones(
        self,
        route_id: str,
        direction_id: int,
        zone_ids: List[int],
        day_type: str,
        hour: int,
    ) -> List[Dict[str, Any]]:
        """Predicts crowding across multiple contiguous zones on a journey leg."""
        return [
            self.predict_crowd(route_id, direction_id, z, day_type, hour)
            for z in zone_ids
        ]
