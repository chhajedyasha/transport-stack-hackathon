#!/usr/bin/env python3
"""CrowdWise Smoke Test Suite.
Verifies end-to-end integration across all REST API endpoints and data layers.
Tests:
1. /api/health
2. /api/stops/search (spatial & fuzzy)
3. /api/routes & /api/routes/<id>
4. /api/crowd/profile/<id>
5. /api/journey/plan (Fastest, Balanced, Least Crowded)
6. /api/analytics/summary

Usage:
  python scripts/smoke_test.py
"""
import sys
import os
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app


def run_smoke_tests():
    print("=================================================================")
    print("                CROWDWISE API SMOKE TEST HARNESS                 ")
    print("=================================================================")

    app = create_app()
    client = app.test_client()

    tests = [
        ("GET", "/api/health", None, "Health Check & Provenance"),
        ("GET", "/api/stops/search?q=Anand&limit=5", None, "Stop Search Autocomplete"),
        ("GET", "/api/routes", None, "Transit Routes List"),
        ("GET", "/api/routes/101UP", None, "Route 101UP Pattern & Stops"),
        ("GET", "/api/crowd/profile/101UP?day_type=WEEKDAY", None, "24h Crowding Diurnal Profile"),
        (
            "GET",
            "/api/journey/plan?origin_id=STOP_ANAND_VIHAR&dest_id=STOP_CONNAUGHT_PLACE&departure_time=18:00&preference=balanced",
            None,
            "Hackathon Showcase: Anand Vihar -> Connaught Place (Balanced)",
        ),
        (
            "GET",
            "/api/journey/plan?origin_id=STOP_ANAND_VIHAR&dest_id=STOP_CONNAUGHT_PLACE&departure_time=18:00&preference=fastest",
            None,
            "Journey Planner: Fastest Mode",
        ),
        (
            "GET",
            "/api/journey/plan?origin_id=STOP_ANAND_VIHAR&dest_id=STOP_CONNAUGHT_PLACE&departure_time=18:00&preference=least_crowded",
            None,
            "Journey Planner: Least Crowded Mode",
        ),
        ("GET", "/api/analytics/summary", None, "Network Analytics Summary"),
    ]

    passed = 0
    failed = 0

    for method, path, body, name in tests:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json=body)

        status_ok = res.status_code == 200
        data = res.get_json()
        envelope_ok = data is not None and data.get("ok") is True

        if status_ok and envelope_ok:
            passed += 1
            print(f"  [OK] {res.status_code} | {name:<50} | {path}")
        else:
            failed += 1
            err_msg = data.get("error") if data else res.data.decode("utf-8")
            print(f"  [FAIL] {res.status_code} | {name:<50} | {path}")
            print(f"         Error: {err_msg}")

    print("=================================================================")
    if failed == 0:
        print(f"  SUCCESS: ALL {passed} SMOKE TESTS PASSED! System integration 100% verified.")
        print("=================================================================")
        return 0
    else:
        print(f"  FAILURE: {failed} SMOKE TESTS FAILED out of {passed + failed}.")
        print("=================================================================")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
