"""Multi-modal bus stop search (text, prefix, fuzzy, coordinate-based nearest) with boundary safety."""
import time
from typing import List, Dict, Any, Optional
from flask import Blueprint, request
from sqlalchemy import select
from app import db
from app.models.transit import DimStop
from app.services.gtfs_service import load_all_stops
from app.services.stop_search_service import StopSearchEngine
from app.utils.envelope import api_response

bp = Blueprint("stops", __name__)

_search_engine: Optional[StopSearchEngine] = None


def get_search_engine() -> Optional[StopSearchEngine]:
    global _search_engine
    try:
        stops = load_all_stops(db.session)
        if not stops:
            _search_engine = None
            return None
        if _search_engine is None or len(_search_engine.stops) != len(stops):
            _search_engine = StopSearchEngine(stops)
    except Exception:
        _search_engine = None
    return _search_engine


@bp.route("/search", methods=["GET"])
@bp.route("", methods=["GET"])
def search_stops():
    """Multi-modal stop search supporting text/fuzzy queries AND coordinate proximity."""
    t0 = time.time()
    query = request.args.get("q", "").strip()
    
    # Safe limit parsing
    try:
        limit = min(50, max(1, int(request.args.get("limit", 15))))
    except (ValueError, TypeError):
        limit = 15

    # Check if coordinate search is requested via lat/lon
    raw_lat = request.args.get("lat") or request.args.get("latitude")
    raw_lon = request.args.get("lon") or request.args.get("lng") or request.args.get("longitude")
    
    if raw_lat is not None and raw_lon is not None:
        try:
            f_lat = float(raw_lat)
            f_lon = float(raw_lon)
        except (ValueError, TypeError):
            return api_response(
                error={"code": "INVALID_COORDINATES", "message": "lat and lon must be valid floats"},
                status_code=400,
                start_time=t0,
            )
            
        # Geographic bounds check for Delhi NCR envelope
        # If coordinates are completely out of range (e.g. 0.0, 0.0 or outside NCR)
        if not (28.0 <= f_lat <= 29.5 and 76.5 <= f_lon <= 77.8):
            return api_response(
                data=[],
                data_tier="real_public",
                warning="No bus stops found within radius",
                start_time=t0,
            )
            
        try:
            radius_km = float(request.args.get("radius", request.args.get("radius_km", 5.0)))
        except (ValueError, TypeError):
            radius_km = 5.0
            
        engine = get_search_engine()
        if engine:
            matches = engine.search_nearest(f_lat, f_lon, radius_km=radius_km, limit=limit)
            results = [
                {
                    "stop_id": m.get("stop_id", ""),
                    "stop_code": m.get("stop_code", ""),
                    "stop_name": m.get("stop_name", ""),
                    "stop_lat": m.get("stop_lat", 0.0),
                    "stop_lon": m.get("stop_lon", 0.0),
                    "dist_km": round(float(m.get("distance_km", 0.0)), 2),
                    "distance_km": round(float(m.get("distance_km", 0.0)), 3),
                }
                for m in matches
            ]
            return api_response(data=results, data_tier="real_public", start_time=t0)
        else:
            return api_response(data=[], data_tier="real_public", start_time=t0, warning="Search engine uninitialized")

    # If empty query and no coordinates, return empty list []
    if not query:
        return api_response(data=[], data_tier="real_public", start_time=t0)

    # Text / Prefix / Fuzzy search
    engine = get_search_engine()
    if engine:
        matches = engine.search_text(query, limit=limit)
        results = [
            {
                "stop_id": m.get("stop_id", ""),
                "stop_code": m.get("stop_code", ""),
                "stop_name": m.get("stop_name", ""),
                "stop_lat": m.get("stop_lat", 0.0),
                "stop_lon": m.get("stop_lon", 0.0),
            }
            for m in matches
        ]
    else:
        # Fallback to direct DB query
        try:
            stmt = select(DimStop).where(
                (DimStop.stop_name.ilike(f"%{query}%")) | (DimStop.stop_code.ilike(f"%{query}%"))
            ).limit(limit)
            stops = db.session.execute(stmt).scalars().all()
            results = [
                {
                    "stop_id": s.stop_id,
                    "stop_code": s.stop_code,
                    "stop_name": s.stop_name,
                    "stop_lat": s.stop_lat,
                    "stop_lon": s.stop_lon,
                }
                for s in stops
            ]
        except Exception:
            results = []

    return api_response(data=results, data_tier="real_public", start_time=t0)


@bp.route("/nearby", methods=["GET"])
def nearby_stops():
    """Finds nearest bus stops by GPS coordinate (lat/lon)."""
    t0 = time.time()
    try:
        lat = float(request.args.get("lat", request.args.get("latitude", 0.0)))
        lon = float(request.args.get("lon", request.args.get("lng", request.args.get("longitude", 0.0))))
        radius_km = float(request.args.get("radius", request.args.get("radius_km", 2.0)))
        k = min(20, max(1, int(request.args.get("k", 5))))
    except (ValueError, TypeError):
        return api_response(
            error={"code": "INVALID_COORDINATES", "message": "lat and lon must be valid floats"},
            status_code=400,
            start_time=t0,
        )
        
    engine = get_search_engine()
    if engine:
        matches = engine.search_nearest(lat, lon, radius_km=radius_km, limit=k)
        results = [
            {
                "stop_id": m.get("stop_id", ""),
                "stop_code": m.get("stop_code", ""),
                "stop_name": m.get("stop_name", ""),
                "stop_lat": m.get("stop_lat", 0.0),
                "stop_lon": m.get("stop_lon", 0.0),
                "distance_km": round(float(m.get("distance_km", 0.0)), 3),
                "dist_km": round(float(m.get("distance_km", 0.0)), 2),
            }
            for m in matches
        ]
    else:
        results = []
        
    return api_response(data=results, data_tier="real_public", start_time=t0)
