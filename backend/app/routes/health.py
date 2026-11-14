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
        "data_mode": current_app.config.get("DATA_MODE", "organizer"),
        "active_tier": "organizer",
        "routes_indexed": routes_count,
        "stops_indexed": stops_count,
    }
    
    warning = "Database unseeded - run bootstrap.py to ingest GTFS and organizer data" if is_unseeded else None

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
    mode = current_app.config.get("DATA_MODE", "organizer")
    
    data = {
        "project": "CrowdWise",
        "description": "Crowdedness-aware bus journey planner for Delhi (Transport Stack Hackathon 2026)",
        "version": "1.0.0",
        "data_mode": mode,
        "active_tier": "organizer",
        "date_range": {
            "start": "2026-10-01",
            "end": "2026-10-31",
            "total_days": 31,
        },
        "datasets": [
            {
                "name": "October-Delhi.csv",
                "tier": "organizer",
                "role": "Conductor ETM ticketing logs",
                "records": 2559899,
                "file_size_mb": 276.6,
                "coverage_days": 31,
            },
            {
                "name": "Delhi Static GTFS Timetable",
                "tier": "real_public",
                "role": "Authentic transit stops, routes, timetables, and shapes",
                "stops": 6862,
                "routes": 2574,
                "patterns": 3498,
                "pattern_stops": 109660,
            },
        ],
        "cleaning_funnel": {
            "raw_tickets": 2559899,
            "mode_a_exact_od_matches": 1979418,
            "mode_a_match_pct": 77.32,
            "mode_b_inferred_matches": 283240,
            "mode_b_match_pct": 11.06,
            "total_staged_zone_demand_facts": 3322312,
        },
        "provenance_tiers": {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetables)",
            "organizer": "Official Delhi Transport Stack ETM records (Oct 2026)",
            "estimated": "Reconstructed passenger loads and Random Forest predictions",
        },
        "estimation_mode": {
            "mode": "Mode A (Exact O-D Boardings & Alightings) with Mode B Fallback",
            "conservation_formula": "L_s = max(0, L_{s-1} + gamma_r * b_s - a_s)",
            "pink_pass_expansion_gamma": 1.30,
            "bus_nominal_capacity": 60,
        },
        "model_metadata": ml_service.metadata,
    }
    return api_response(data=data, data_tier="real_public", start_time=t0)


@bp.route("/data-tier", methods=["GET"])
def get_data_tier():
    """Returns current active data tier flag and complete provenance disclosures."""
    t0 = time.time()
    mode = current_app.config.get("DATA_MODE", "organizer")
    
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

    active_tier = "organizer" if mode in ("organizer", "production", "live") else "real_public"
    is_demo = False
    
    data = {
        "data_mode": mode,
        "active_tier": active_tier,
        "is_demo": is_demo,
        "provenance_tiers": {
            "real_public": "Delhi Buses static GTFS (routes, stops, timetables)",
            "organizer": "Official Delhi Transport Stack ETM records (Oct 2026)",
            "estimated": "Reconstructed passenger loads and Random Forest predictions",
        },
    }
    return api_response(data=data, data_tier="real_public", start_time=t0)
