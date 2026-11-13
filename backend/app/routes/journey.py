"""Journey planning endpoint."""
import time
from flask import Blueprint, request
from app import db
from app.services.planner_service import JourneyPlannerService
from app.utils.envelope import api_response

bp = Blueprint("journey", __name__, url_prefix="/api/journey")


@bp.route("/plan", methods=["POST"])
def plan_journey():
    """Generates direct route candidates scored by time, wait, and crowdedness."""
    t0 = time.time()
    body = request.get_json(silent=True) or {}
    
    origin_id = body.get("origin_stop_id") or body.get("origin_id")
    dest_id = body.get("destination_stop_id") or body.get("destination_id")
    
    if not origin_id or not dest_id:
        return api_response(
            error={
                "code": "MISSING_STOPS",
                "message": "Both 'origin_stop_id' and 'destination_stop_id' are required.",
            },
            status_code=400,
            start_time=t0,
        )
        
    departure_time = body.get("departure_time")
    day_type = body.get("day_type", "WEEKDAY")
    preference = body.get("preference", "balanced")
    
    planner = JourneyPlannerService(db.session)
    result = planner.plan_journey(
        origin_stop_id=str(origin_id),
        destination_stop_id=str(dest_id),
        departure_time=departure_time,
        day_type=day_type,
        preference=preference,
        origin_lat=body.get("origin_lat"),
        origin_lon=body.get("origin_lon"),
        dest_lat=body.get("dest_lat"),
        dest_lon=body.get("dest_lon"),
    )
    
    return api_response(data=result, start_time=t0)
