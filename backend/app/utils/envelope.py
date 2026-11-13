"""Standard API response envelope helper."""
from datetime import datetime, timezone
import time
from typing import Any, Optional
from flask import jsonify, current_app, request


def api_response(
    data: Any = None,
    error: Optional[Dict[str, Any]] = None,
    status_code: int = 200,
    data_tier: Optional[str] = None,
    start_time: Optional[float] = None,
):
    """Generates consistent API envelope for all CrowdWise endpoints."""
    elapsed_ms = round((time.time() - start_time) * 1000.0, 2) if start_time else 0.0
    
    tier = data_tier or getattr(current_app.config, "DATA_MODE", "demo")
    # Map tier string
    tier_label = "demo_synthetic" if tier == "demo" else ("organizer" if tier == "organizer" else tier)
    
    envelope = {
        "ok": error is None and status_code < 400,
        "data": data,
        "error": error,
        "meta": {
            "version": "1.0.0",
            "data_tier": tier_label,
            "provenance": {
                "timetable": "real_public",
                "tickets": tier_label,
                "crowd": "estimated",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_time_ms": elapsed_ms,
        },
    }
    return jsonify(envelope), status_code
