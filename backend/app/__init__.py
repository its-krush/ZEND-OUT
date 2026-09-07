import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from .extensions import csrf, db, limiter

load_dotenv()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///zendout.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        WTF_CSRF_TIME_LIMIT=3600,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    if app.config["SECRET_KEY"] == "dev-only-change-me" and os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY must be set in production")
    origins = [x.strip() for x in os.environ.get("FRONTEND_ORIGINS", "http://localhost:8000").split(",") if x.strip()]
    CORS(app, origins=origins, supports_credentials=True, methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"])
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="request_too_large"), 413

    with app.app_context():
        db.create_all()
    return app


app = create_app()
