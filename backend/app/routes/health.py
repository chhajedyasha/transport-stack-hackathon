"""Health check, metadata, and data tier disclosures."""
import time
from flask import Blueprint, current_app
from sqlalchemy import text, select, func
from app.utils.envelope import api_response
from app.services.ml_service import MLService
from app.models.transit import DimRoute, DimStop
from app.models.demand import SysRuntimeMetadata

bp = Blueprint("health", __name__)


@bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint reporting DB, model, and index statistics."""
    t0 = time.time()
    
    db_ok = True
    db_msg = "healthy"
    routes_count = 0
    stops_count = 0
    
    try:
        from app import db
        db.session.execute(text("SELECT 1")).scalar()
        routes_count = db.session.execute(select(func.count(DimRoute.route_id))).scalar() or 0
        stops_count = db.session.execute(select(func.count(DimStop.stop_id))).scalar() or 0
        db_uri = str(current_app.config.get("SQLALCHEMY_DATABASE_URI", ""))
        db_msg = "sqlite_connected" if "sqlite" in db_uri else "postgresql_connected"
    except Exception as e:
        db_ok = False
        db_msg = f"unhealthy: {e}"
        
    ml_service = MLService.get_instance()
    ml_status = "loaded" if ml_service.is_loaded else "degraded_heuristic_fallback"
    
    # Degraded mode if DB unreachable or unseeded
    is_unseeded = db_ok and stops_count == 0
    is_degraded = not db_ok or is_unseeded or not ml_service.is_loaded

    status_str = "healthy"
    if not db_ok:
        status_str = "unhealthy"
    elif is_unseeded:
        status_str = "unseeded"
    elif is_degraded:
        status_str = "degraded"

    data = {
        "status": status_str,
        "database": db_msg,
        "ml_model": ml_status,
        "model_loaded": ml_service.is_loaded,
        "data_mode": current_app.config.get("DATA_MODE", "demo"),
        "routes_indexed": routes_count,
        "stops_indexed": stops_count,
    }
    
    warning = "Database unseeded - run bootstrap.py --demo to ingest GTFS" if is_unseeded else None

    return api_response(
        data=data,
        data_tier="real_public",
        start_time=t0,
        degraded_mode=is_degraded,
        warning=warning,
    )


@bp.route("/meta", methods=["GET"])
def get_metadata():
    """System metadata and provenance information."""
    t0 = time.time()
    ml_service = MLService.get_instance()
    mode = current_app.config.get("DATA_MODE", "demo")
    
    data = {
        "project": "CrowdWise",
        "description": "Crowdedness-aware bus journey planner for Delhi (Transport Stack Hackathon 2026)",
        "version": "1.0.0",
        "data_mode": mode,
        "provenance_tiers": {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetables)",
            "organizer": "Official Delhi Transport Stack ETM records (Oct 2026)",
            "demo_synthetic": "High-fidelity synthetic passenger flow simulator",
            "estimated": "Reconstructed passenger loads and Random Forest predictions",
        },
        "model_metadata": ml_service.metadata,
    }
    return api_response(data=data, data_tier="real_public", start_time=t0)


@bp.route("/data-tier", methods=["GET"])
def get_data_tier():
    """Returns current active data tier flag and complete provenance disclosures."""
    t0 = time.time()
    mode = current_app.config.get("DATA_MODE", "demo")
    
    # Check DB runtime metadata if available
    try:
        from app import db
        meta_row = db.session.execute(
            select(SysRuntimeMetadata).where(SysRuntimeMetadata.key == "data_mode")
        ).scalar_one_or_none()
        if meta_row and meta_row.value:
            mode = meta_row.value
    except Exception:
        pass

    active_tier = "organizer" if mode in ("organizer", "production", "live") else "demo_synthetic"
    is_demo = mode == "demo"
    
    data = {
        "data_mode": mode,
        "active_tier": active_tier,
        "is_demo": is_demo,
        "provenance_tiers": {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetables)",
            "organizer": "Official Delhi Transport Stack ETM records (Oct 2026)",
            "demo_synthetic": "High-fidelity synthetic passenger flow simulator",
            "estimated": "Reconstructed passenger loads and Random Forest predictions",
        },
    }
    return api_response(data=data, data_tier="real_public", start_time=t0)
