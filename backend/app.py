"""Flask application factory for the Qadam Club API and static frontends."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from flasgger import Swagger
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Settings, load_settings

from . import database
from .errors import ServiceError

logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

SWAGGER_TEMPLATE = {
    "info": {
        "title": "Qadam Club API",
        "description": "Habit-tracking challenges for a Telegram Mini App.",
        "version": "1.0.0",
    },
    "securityDefinitions": {
        "TelegramInitData": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "`tma <window.Telegram.WebApp.initData>`",
        },
        "AdminToken": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "`Bearer <ADMIN_API_TOKEN>`",
        },
    },
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: rule.rule.startswith("/api/"),
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
) -> Flask:
    settings = settings or load_settings()

    app = Flask(__name__)
    app.config["SETTINGS"] = settings
    app.config["CLOCK"] = clock or (lambda: datetime.now(settings.tz))
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.json.sort_keys = False

    Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)

    database.init_engine(settings.database_url)
    database.init_db(settings.admin_ids)
    # Drop connections opened during start-up so forked gunicorn workers
    # (``--preload``) never share a connection with the master process.
    database.release_connections()

    if not settings.bot_token:
        logger.warning("BOT_TOKEN is not set: Mini App endpoints will answer 503")
    if not settings.admin_api_token:
        logger.warning("ADMIN_API_TOKEN is not set: admin API only accepts admin initData")

    from .routes.admin import admin_bp
    from .routes.auth import auth_bp
    from .routes.challenges import challenges_bp
    from .routes.leaderboard import leaderboard_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(challenges_bp, url_prefix="/api/challenges")
    app.register_blueprint(leaderboard_bp, url_prefix="/api/leaderboard")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    _register_error_handlers(app)
    _register_core_routes(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ServiceError)
    def handle_service_error(exc: ServiceError):
        return jsonify({"error": exc.message, "code": exc.code}), exc.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        return jsonify({"error": exc.description, "code": exc.name.lower().replace(" ", "_")}), (
            exc.code or 500
        )

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):  # pragma: no cover - safety net
        logger.exception("unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "Internal server error", "code": "internal_error"}), 500


def _register_core_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        return {"status": "ok", "message": "Qadam Club API is running"}

    @app.route("/healthz")
    def healthz():
        """Liveness/readiness probe used by Docker; also checks the database."""
        if database.ping():
            return {"status": "ok", "database": "ok"}
        return {"status": "degraded", "database": "unreachable"}, 503

    @app.route("/tma")
    @app.route("/tma/")
    def serve_tma():
        return send_from_directory(FRONTEND_DIR / "tma", "index.html")

    @app.route("/admin-panel")
    def serve_admin():
        return send_from_directory(FRONTEND_DIR / "admin", "index.html")


def main() -> None:  # pragma: no cover - development server only
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = load_settings()
    app = create_app(settings)
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=settings.debug)


if __name__ == "__main__":  # pragma: no cover
    main()
