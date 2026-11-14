import subprocess
import os
import sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = os.path.abspath(r"transport-stack-hackathon\docs\design\before")
os.makedirs(OUT_DIR, exist_ok=True)

targets = [
    ("planner", "http://localhost:3000/"),
    ("results", "http://localhost:3000/results?origin_id=8256&dest_id=365&departure_time=18:00&preference=balanced"),
    ("route", "http://localhost:3000/route/101UP"),
    ("analytics", "http://localhost:3000/analytics"),
    ("about", "http://localhost:3000/about")
]

viewports = [
    ("mobile_360", 360, 640),
    ("tablet_768", 768, 1024),
    ("desktop_1440", 1440, 900)
]

for name, url in targets:
    for vp_name, w, h in viewports:
        out_file = os.path.join(OUT_DIR, f"{name}_{vp_name}.png")
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            f"--window-size={w},{h}",
            f"--screenshot={out_file}",
            "--virtual-time-budget=3000",
            url
        ]
        print(f"Capturing {name} {vp_name} ({w}x{h})...")
        try:
            subprocess.run(cmd, capture_output=True, timeout=12)
        except Exception as e:
            print(f"Error {name} {vp_name}: {e}")

print("All before screenshots saved to docs/design/before/.")
