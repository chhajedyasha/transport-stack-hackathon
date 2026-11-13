"""Application configuration settings."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "crowdwise-hackathon-secret-key-2026")
    
    # Dual-dialect database URL (SQLite default, PostgreSQL via env)
    DEFAULT_SQLITE_PATH = BASE_DIR / "crowdwise.db"
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Data Mode: 'demo' (synthetic) or 'organizer' (official ETM)
    DATA_MODE = os.getenv("DATA_MODE", "demo")
    
    # Models path
    MODELS_DIR = BASE_DIR.parent / "models"
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

