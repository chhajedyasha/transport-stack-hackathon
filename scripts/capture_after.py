import subprocess
import os
import sys
import tempfile
import time

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = os.path.abspath(r"transport-stack-hackathon\docs\design\after")
os.makedirs(OUT_DIR, exist_ok=True)

targets = [
    ("planner", "http://localhost:3000/"),
    ("results", "http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=balanced"),
    ("route", "http://localhost:3000/route/101UP"),
    ("analytics", "http://localhost:3000/analytics"),
    ("about", "http://localhost:3000/about"),
]

viewports = [
    ("mobile_320", 320, 568),
    ("mobile_360", 360, 640),
    ("tablet_768", 768, 1024),
    ("desktop_1440", 1440, 900),
]

for name, url in targets:
    for vp_name, w, h in viewports:
        out_file = os.path.join(OUT_DIR, f"{name}_{vp_name}.png")
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
        print(f"Capturing {name}_{vp_name} ({w}x{h})...", flush=True)
        try:
            subprocess.run(cmd, capture_output=True, timeout=10)
            if os.path.exists(out_file) and os.path.getsize(out_file) > 1000:
                print(f" -> Saved {name}_{vp_name}.png ({os.path.getsize(out_file)} bytes)", flush=True)
        except Exception as e:
            print(f"Error {name}_{vp_name}: {e}", flush=True)

print("All after screenshots complete.", flush=True)
