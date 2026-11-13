import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app

def verify():
    app = create_app()
    client = app.test_client()

    print("==================================================================")
    print("           VERIFYING COMPLETE FULL-STACK WEBSITE (10/10)          ")
    print("==================================================================")

    # 1. Frontend Homepage
    r1 = client.get("/")
    assert r1.status_code == 200, f"Root failed: {r1.status_code}"
    assert b"CrowdWise" in r1.data, "CrowdWise not found in root"
    print(f"1. [PASS] Homepage HTML: Status 200 (Length: {len(r1.data)} bytes)")

    # 2. Results page SPA routing
    r2 = client.get("/results?origin_id=STOP_ANAND_VIHAR&dest_id=STOP_CONNAUGHT_PLACE")
    assert r2.status_code == 200
    assert b"root" in r2.data
    print(f"2. [PASS] Results Page SPA Fallback: Status 200")

    # 3. Route Details SPA routing
    r3 = client.get("/route/101UP")
    assert r3.status_code == 200
    assert b"root" in r3.data
    print(f"3. [PASS] Route Details SPA Fallback: Status 200")

    # 4. Analytics SPA routing
    r4 = client.get("/analytics")
    assert r4.status_code == 200
    assert b"root" in r4.data
    print(f"4. [PASS] Analytics Page SPA Fallback: Status 200")

    # 5. About / Methodology SPA routing
    r5 = client.get("/about")
    assert r5.status_code == 200
    assert b"root" in r5.data
    print(f"5. [PASS] About Page SPA Fallback: Status 200")

    # 6. Journey Planner API
    r6 = client.get("/api/journey/plan?origin_id=STOP_ANAND_VIHAR&dest_id=STOP_CONNAUGHT_PLACE&departure_time=18:00&preference=balanced")
    assert r6.status_code == 200
    d6 = r6.get_json()
    assert d6["ok"] is True
    opts = d6["data"]["options"]
    print(f"6. [PASS] Journey Planner API: Status 200 ({len(opts)} options returned)")
    for opt in opts:
        print(f"   -> Bus {opt.get('route_short_name')}: {opt.get('total_duration_minutes')} min | {opt.get('crowd_category')} | RCI: {opt.get('avg_rci')}")

    # 7. Spatial & Fuzzy Stop Search API
    r7 = client.get("/api/stops/search?q=Anand&limit=3")
    assert r7.status_code == 200
    d7 = r7.get_json()
    matches = d7["data"] if isinstance(d7["data"], list) else d7["data"].get("matches", [])
    print(f"7. [PASS] Stop Search API: Status 200 ({len(matches)} matches for 'Anand')")
    for m in matches:
        print(f"   -> Stop: {m.get('stop_name')} ({m.get('stop_id')})")

    # 8. Route Corridor Details API
    r8 = client.get("/api/routes/101UP")
    assert r8.status_code == 200
    d8 = r8.get_json()
    stops = d8["data"]["stops"]
    print(f"8. [PASS] Route Details API: Status 200 ({len(stops)} stops mapped)")

    # 9. 24h Crowding Diurnal Profile API
    r9 = client.get("/api/crowd/profile/101UP?day_type=WEEKDAY")
    assert r9.status_code == 200
    d9 = r9.get_json()
    hp = d9["data"]["hourly_profile"]
    zp = d9["data"]["zone_profiles"]
    print(f"9. [PASS] 24h Diurnal Profile API: Status 200 ({len(hp)} hours, {len(zp)} zones)")

    # 10. Analytics Summary API
    r10 = client.get("/api/analytics/summary")
    assert r10.status_code == 200
    d10 = r10.get_json()
    print(f"10. [PASS] Network Analytics API: Status 200 (Total routes: {d10['data']['total_routes']})")

    print("==================================================================")
    print("  ALL 10 FULL-STACK VERIFICATION CHECKS PASSED WITH ZERO ERRORS!  ")
    print("==================================================================")

if __name__ == "__main__":
    verify()
