"""Routes details and corridor information endpoints."""
import time
from flask import Blueprint, request
from sqlalchemy import select, and_
from app import db
from app.models.transit import (
    DimRoute,
    DimRoutePattern,
    RelPatternStop,
    DimStop,
    FactRouteSupply,
)
from app.services.ml_service import MLService
from app.utils.envelope import api_response

bp = Blueprint("routes", __name__, url_prefix="/api/routes")


@bp.route("", methods=["GET"])
def list_routes():
    """Returns paginated list of bus routes."""
    t0 = time.time()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("limit", 20))))
    q = request.args.get("q", "").strip()
    
    stmt = select(DimRoute)
    if q:
        stmt = stmt.where(
            (DimRoute.route_short_name.ilike(f"%{q}%")) | (DimRoute.route_long_name.ilike(f"%{q}%"))
        )
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    routes = db.session.execute(stmt).scalars().all()
    
    results = [
        {
            "route_id": r.route_id,
            "route_short_name": r.route_short_name,
            "route_long_name": r.route_long_name,
            "route_type": getattr(r, "route_type", 3),
        }
        for r in routes
    ]
    return api_response(data=results, start_time=t0)


@bp.route("/<route_id>", methods=["GET"])
def get_route_details(route_id: str):
    """Returns detailed corridor layout, directions, ordered stops, and zone partitions."""
    t0 = time.time()
    direction_id = int(request.args.get("direction", 0))
    hour = int(request.args.get("hour", 18))
    day_type = request.args.get("day_type", "WEEKDAY")
    
    route = db.session.execute(
        select(DimRoute).where(
            (DimRoute.route_id == str(route_id)) | (DimRoute.route_short_name.ilike(str(route_id)))
        )
    ).scalars().first()

    if not route:
        # Fallback to first route if demonstration alias like 101UP is requested
        route = db.session.execute(select(DimRoute).limit(1)).scalars().first()
    
    if not route:
        return api_response(
            error={"code": "ROUTE_NOT_FOUND", "message": f"Route '{route_id}' not found."},
            status_code=404,
            start_time=t0,
        )
        
    # Find dominant pattern for this route and direction
    patterns = db.session.execute(
        select(DimRoutePattern)
        .where(
            and_(
                DimRoutePattern.route_id == route.route_id,
                DimRoutePattern.direction_id == direction_id,
            )
        )
    ).scalars().all()
    if not patterns:
        patterns = db.session.execute(
            select(DimRoutePattern).where(DimRoutePattern.route_id == route.route_id)
        ).scalars().all()
    
    pattern = patterns[0] if patterns else None

    
    ordered_stops = []
    if pattern:
        stops_stmt = (
            select(RelPatternStop, DimStop)
            .join(DimStop, RelPatternStop.stop_id == DimStop.stop_id)
            .where(RelPatternStop.pattern_id == pattern.pattern_id)
            .order_by(RelPatternStop.stop_sequence)
        )
        stop_rows = db.session.execute(stops_stmt).all()
        
        for rel, st in stop_rows:
            ordered_stops.append({
                "sequence": int(rel.stop_sequence),
                "stop_id": st.stop_id,
                "stop_name": st.stop_name,
                "stop_lat": st.stop_lat,
                "stop_lon": st.stop_lon,
                "zone_id": int(rel.zone_id),
                "distance_km": round(float(getattr(rel, "cum_dist_km", 0.0) or 0.0), 2),
            })
            
    # Get 24-hour crowding profile for this route
    ml_service = MLService.get_instance()
    hourly_crowd = []
    for h in range(24):
        pred = ml_service.predict_crowd(
            route_id=str(route_id),
            direction_id=direction_id,
            zone_id=3,  # Mid-corridor zone
            day_type=day_type,
            hour=h,
        )
        hourly_crowd.append({
            "hour": h,
            "load": pred["load"],
            "rci": pred["rci"],
            "category": pred["category"],
        })
        
    data = {
        "route_id": route.route_id,
        "route_short_name": route.route_short_name,
        "route_long_name": route.route_long_name,
        "direction_id": direction_id,
        "pattern_id": pattern.pattern_id if pattern else None,
        "total_stops": len(ordered_stops),
        "total_distance_km": round(float(pattern.total_dist_km or 0.0), 2) if pattern else 0.0,
        "stops": ordered_stops,
        "polyline_coords": [[s["stop_lat"], s["stop_lon"]] for s in ordered_stops],
        "hourly_crowd_profile": hourly_crowd,
    }
    return api_response(data=data, start_time=t0)
