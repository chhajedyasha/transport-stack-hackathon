import subprocess
import os
import sys
import tempfile
import time

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = os.path.abspath(r"transport-stack-hackathon\docs\design\after")
os.makedirs(OUT_DIR, exist_ok=True)

targets = [
    ("planner_360", "http://localhost:3000/", 360, 640),
    ("planner_1440", "http://localhost:3000/", 1440, 900),
    ("results_360", "http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=balanced", 360, 640),
    ("results_1440", "http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=balanced", 1440, 900),
    ("route_768", "http://localhost:3000/route/101UP", 768, 1024),
    ("analytics_768", "http://localhost:3000/analytics", 768, 1024),
    ("about_768", "http://localhost:3000/about", 768, 1024),
]

for name, url, w, h in targets:
    out_file = os.path.join(OUT_DIR, f"{name}.png")
    temp_profile = tempfile.mkdtemp()
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--user-data-dir={temp_profile}",
        f"--window-size={w},{h}",
        f"--screenshot={out_file}",
        url
    ]
    print(f"Capturing {name} ({w}x{h})...", flush=True)
    try:
        subprocess.run(cmd, capture_output=True, timeout=8)
        if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
            print(f" -> Saved {name}.png ({os.path.getsize(out_file)} bytes)", flush=True)
    except Exception as e:
        print(f"Error {name}: {e}", flush=True)

print("All after screenshots complete.", flush=True)
