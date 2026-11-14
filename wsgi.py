"""WSGI entrypoint for CrowdWise Flask backend."""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(ROOT_DIR))

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("true", "1")
    use_reloader = os.getenv("FLASK_RELOAD", "0").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=use_reloader, threaded=True)
