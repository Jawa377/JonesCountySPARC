"""Application factory: builds, configures, and wires up the Flask app."""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

from app.db_connect import close_db

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAX_UPLOAD_MB = 25


def load_config(app: Flask, test_config: dict | None) -> None:
    """Read settings from the environment (.env locally), then apply overrides.

    Raises RuntimeError if FLASK_SECRET_KEY is missing (no fallback, by rule)
    or DATABASE_ENGINE isn't sqlite/mysql.
    """
    load_dotenv(PROJECT_ROOT / ".env")
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        DATABASE_ENGINE=os.environ.get("DATABASE_ENGINE", "sqlite").strip().lower(),
        SQLITE_PATH=os.environ.get("SQLITE_PATH", str(PROJECT_ROOT / "database" / "sparc.db")),
        JAWSDB_URL=os.environ.get("JAWSDB_URL"),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_MB * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    sqlite_path = Path(app.config["SQLITE_PATH"])
    if not sqlite_path.is_absolute():
        app.config["SQLITE_PATH"] = str(PROJECT_ROOT / sqlite_path)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("FLASK_SECRET_KEY is not set. Add it to .env (see .env.example).")
    if app.config["DATABASE_ENGINE"] not in ("sqlite", "mysql"):
        raise RuntimeError("DATABASE_ENGINE must be 'sqlite' or 'mysql'.")


def register_blueprints(app: Flask) -> None:
    """Attach every feature blueprint at its singular URL prefix."""
    from app.routes import bp as main_bp
    from app.blueprints.teachers import bp as teachers_bp
    from app.blueprints.units import bp as units_bp
    from app.blueprints.materials import bp as materials_bp
    from app.blueprints.standards import bp as standards_bp
    from app.blueprints.studios import bp as studios_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(teachers_bp, url_prefix="/teacher")
    app.register_blueprint(units_bp, url_prefix="/unit")
    app.register_blueprint(materials_bp, url_prefix="/material")
    app.register_blueprint(standards_bp, url_prefix="/standard")
    app.register_blueprint(studios_bp, url_prefix="/studio")


def register_error_pages(app: Flask) -> None:
    """Render friendly pages for missing records, big uploads, and a down database."""
    def render_error(status: int, title: str, message: str):
        return render_template("error.html", status=status, title=title, message=message), status

    app.register_error_handler(
        404, lambda e: render_error(404, "Not found", "That page doesn't exist, or it belongs to another teacher.")
    )
    app.register_error_handler(
        413, lambda e: render_error(413, "File too large", f"Uploads are limited to {MAX_UPLOAD_MB} MB.")
    )
    app.register_error_handler(
        ConnectionError,
        lambda e: render_error(503, "Database unavailable", "The database can't be reached right now. Check the server log."),
    )


def register_template_context(app: Flask) -> None:
    """Make current_teacher available to every template (None if unknown or DB down)."""
    from app.functions import get_current_teacher

    def inject_current_teacher():
        try:
            return {"current_teacher": get_current_teacher()}
        except ConnectionError:
            return {"current_teacher": None}

    app.context_processor(inject_current_teacher)


def ordinal(number: int) -> str:
    """Jinja filter: 6 -> "6th", 1 -> "1st", 22 -> "22nd", 11 -> "11th"."""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"


def create_app(test_config: dict | None = None) -> Flask:
    """Build the SPARC Textbook Studio app.

    Input: optional config overrides (tests pass SQLITE_PATH, SECRET_KEY, etc.).
    Output: a configured Flask app. No database connection is opened here;
    connections open lazily per request.
    """
    app = Flask(__name__)
    load_config(app, test_config)
    register_blueprints(app)
    register_error_pages(app)
    register_template_context(app)
    app.add_template_filter(ordinal)
    app.teardown_appcontext(close_db)
    return app
