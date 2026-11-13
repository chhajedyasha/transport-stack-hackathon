"""Health check and metadata endpoints."""
import time
from pathlib import Path
from flask import Blueprint, current_app
from sqlalchemy import text
from app.utils.envelope import api_response
from app.services.ml_service import MLService

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    t0 = time.time()
    
    # Check DB reachability
    db_ok = True
    db_msg = "healthy"
    try:
        from app import db
        db.session.execute(text("SELECT 1")).scalar()
    except Exception as e:
        db_ok = False
        db_msg = f"unhealthy: {e}"
        
    ml_service = MLService.get_instance()
    ml_status = "loaded" if ml_service.is_loaded else "heuristic_fallback"
    
    data = {
        "status": "healthy" if db_ok else "degraded",
        "database": db_msg,
        "ml_model": ml_status,
        "data_mode": current_app.config.get("DATA_MODE", "demo"),
    }
    return api_response(data=data, start_time=t0)


@bp.route("/meta", methods=["GET"])
def get_metadata():
    """System metadata and provenance information."""
    t0 = time.time()
    ml_service = MLService.get_instance()
    
    data = {
        "project": "CrowdWise",
        "description": "Crowdedness-aware bus journey planner for Delhi (Transport Stack Hackathon 2026)",
        "version": "1.0.0",
        "data_mode": current_app.config.get("DATA_MODE", "demo"),
        "provenance_tiers": {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetables)",
            "organizer": "Official Delhi Transport Stack ETM records (Oct 2026)",
            "demo_synthetic": "High-fidelity synthetic passenger flow simulator",
            "estimated": "Reconstructed passenger loads and Random Forest predictions",
        },
        "model_metadata": ml_service.metadata,
    }
    return api_response(data=data, start_time=t0)


@bp.route("/data-tier", methods=["GET"])
def get_data_tier():
    """Returns current active data tier flag."""
    t0 = time.time()
    mode = current_app.config.get("DATA_MODE", "demo")
    return api_response(data={"data_mode": mode, "is_demo": mode == "demo"}, start_time=t0)
