import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from .extensions import csrf, db, limiter

load_dotenv()


def database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///zendout.db")
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=database_url(),
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

    frontend_root = Path(app.root_path).parent.parent

    @app.get("/")
    def frontend_index():
        return send_from_directory(frontend_root, "index.html")

    @app.get("/<path:filename>")
    def frontend_file(filename):
        if filename == "api" or filename.startswith("api/"):
            return jsonify(error="not_found"), 404
        candidate = frontend_root / filename
        if candidate.is_file() and (candidate.suffix.lower() in {".html", ".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"} or filename.startswith("images/")):
            return send_from_directory(frontend_root, filename)
        return jsonify(error="not_found"), 404

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="request_too_large"), 413

    if os.environ.get("AUTO_CREATE_DB", "true").lower() == "true" and os.environ.get("FLASK_ENV", "development") != "production":
        with app.app_context():
            db.create_all()
    return app


app = create_app()
