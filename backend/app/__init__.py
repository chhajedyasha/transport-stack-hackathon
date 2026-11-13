"""Flask application factory for CrowdWise backend."""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from app.utils.envelope import api_response

db = SQLAlchemy()


def create_app(config_class=Config) -> Flask:
    """Application factory for CrowdWise Flask REST API."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Create tables on startup if using SQLite and tables don't exist
    from app.models.transit import Base as TransitBase
    from app.models.demand import Base as DemandBase
    with app.app_context():
        TransitBase.metadata.create_all(db.engine)

    # Register blueprints
    from app.routes.health import bp as health_bp
    from app.routes.stops import bp as stops_bp
    from app.routes.routes import bp as routes_bp
    from app.routes.crowd import bp as crowd_bp
    from app.routes.journey import bp as journey_bp
    from app.routes.analytics import bp as analytics_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(stops_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(crowd_bp)
    app.register_blueprint(journey_bp)
    app.register_blueprint(analytics_bp)

    # Global Error Handlers with standard envelope
    @app.errorhandler(400)
    def bad_request(e):
        return api_response(
            error={"code": "BAD_REQUEST", "message": str(e.description if hasattr(e, "description") else e)},
            status_code=400,
        )

    @app.errorhandler(404)
    def not_found(e):
        return api_response(
            error={"code": "NOT_FOUND", "message": "The requested resource was not found."},
            status_code=404,
        )

    @app.errorhandler(500)
    def server_error(e):
        return api_response(
            error={"code": "INTERNAL_SERVER_ERROR", "message": "An internal server error occurred."},
            status_code=500,
        )

    return app
