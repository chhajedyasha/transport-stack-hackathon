"""Stops search and spatial proximity endpoints."""
import time
from flask import Blueprint, request
from sqlalchemy import select
from app import db
from app.models.transit import DimStop
from app.services.gtfs_service import load_all_stops
from app.services.stop_search_service import StopSearchEngine
from app.utils.envelope import api_response

bp = Blueprint("stops", __name__, url_prefix="/api/stops")

_search_engine = None


def get_search_engine():
    global _search_engine
    if _search_engine is None:
        try:
            stops = load_all_stops(db.session)
            if stops:
                _search_engine = StopSearchEngine(stops)
        except Exception:
            _search_engine = None
    return _search_engine


@bp.route("/search", methods=["GET"])
@bp.route("", methods=["GET"])
def search_stops():
    """Text, prefix, and fuzzy search over bus stops."""
    t0 = time.time()
    query = request.args.get("q", "").strip()
    limit = min(50, max(1, int(request.args.get("limit", 15))))
    
    engine = get_search_engine()
    if engine and query:
        matches = engine.search(query, limit=limit)
        results = [
            {
                "stop_id": m["stop_id"] if isinstance(m, dict) else m.stop_id,
                "stop_code": m["stop_code"] if isinstance(m, dict) else m.stop_code,
                "stop_name": m["stop_name"] if isinstance(m, dict) else m.stop_name,
                "stop_lat": m["stop_lat"] if isinstance(m, dict) else m.stop_lat,
                "stop_lon": m["stop_lon"] if isinstance(m, dict) else m.stop_lon,
            }
            for m in matches
        ]
    else:
        # DB fallback
        stmt = select(DimStop)
        if query:
            stmt = stmt.where(DimStop.stop_name.ilike(f"%{query}%"))
        stmt = stmt.limit(limit)
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
        
    return api_response(data=results, start_time=t0)


@bp.route("/nearby", methods=["GET"])
def nearby_stops():
    """Finds nearest bus stops by GPS coordinate (lat/lon)."""
    t0 = time.time()
    try:
        lat = float(request.args.get("lat", request.args.get("latitude", 0.0)))
        lon = float(request.args.get("lon", request.args.get("lng", request.args.get("longitude", 0.0))))
        radius_km = float(request.args.get("radius", request.args.get("radius_km", 1.0)))
        k = min(20, max(1, int(request.args.get("k", 5))))
    except (ValueError, TypeError):
        return api_response(
            error={"code": "INVALID_COORDINATES", "message": "lat and lon must be valid floats"},
            status_code=400,
            start_time=t0,
        )
        
    engine = get_search_engine()
    if engine:
        matches = engine.nearest(lat, lon, k=k, max_distance_km=radius_km)
        results = [
            {
                "stop_id": m["stop_id"] if isinstance(m, dict) else m.stop_id,
                "stop_code": m["stop_code"] if isinstance(m, dict) else m.stop_code,
                "stop_name": m["stop_name"] if isinstance(m, dict) else m.stop_name,
                "stop_lat": m["stop_lat"] if isinstance(m, dict) else m.stop_lat,
                "stop_lon": m["stop_lon"] if isinstance(m, dict) else m.stop_lon,
                "distance_km": round(dist, 3),
            }
            for m, dist in matches
        ]
    else:
        results = []
        
    return api_response(data=results, start_time=t0)
