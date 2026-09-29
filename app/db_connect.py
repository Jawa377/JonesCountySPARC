"""Database access for SQLite (local) and MySQL (JawsDB).

app.config["DATABASE_ENGINE"] picks the engine: "sqlite" or "mysql".
All SQL in the app is written with %s placeholders; for SQLite they are
rewritten to ?. Every helper returns rows as plain dicts, so blueprints
never need to know which engine is running.

One connection per request, stored on flask.g and closed on teardown.
If the database can't be reached, get_db() returns None and the query
helpers raise ConnectionError, which the app turns into a 503 page.
"""

import os
import sqlite3
from urllib.parse import urlparse

import pymysql
import pymysql.cursors
from flask import current_app, g

INTEGRITY_ERRORS = (sqlite3.IntegrityError, pymysql.err.IntegrityError)


def dict_row(cursor, row) -> dict:
    """sqlite3 row factory: return each row as a {column: value} dict."""
    return {column[0]: value for column, value in zip(cursor.description, row)}


def connect_sqlite(path: str):
    """Open the SQLite file at path, or return None if it doesn't exist.

    sqlite3.connect() would silently create an empty database for a missing
    file, so existence is checked first.
    """
    if not os.path.exists(path):
        current_app.logger.error("SQLite database not found at %s. Run: python database/init_db.py", path)
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = dict_row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_mysql(db_url: str | None):
    """Open a MySQL connection from a mysql://user:pass@host:port/db URL, or return None."""
    if not db_url:
        current_app.logger.error("DATABASE_ENGINE is mysql but JAWSDB_URL is not set.")
        return None
    parsed = urlparse(db_url)
    try:
        return pymysql.connect(
            host=parsed.hostname,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/"),
            port=parsed.port or 3306,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
    except pymysql.MySQLError as exc:
        current_app.logger.error("MySQL connection failed: %s", exc.__class__.__name__)
        return None


def get_db():
    """Return this request's database connection, opening it on first use.

    Returns None if the connection can't be made (logged, never raised).
    """
    if "db" not in g:
        if current_app.config["DATABASE_ENGINE"] == "mysql":
            g.db = connect_mysql(current_app.config.get("JAWSDB_URL"))
        else:
            g.db = connect_sqlite(current_app.config["SQLITE_PATH"])
    return g.db


def require_db():
    """Return the connection, or raise ConnectionError if there isn't one."""
    db = get_db()
    if db is None:
        raise ConnectionError("Database unavailable")
    return db


def close_db(exception=None) -> None:
    """Close the request's connection, if one was opened. Registered as teardown."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def prepare_sql(sql: str) -> str:
    """Rewrite %s placeholders to ? when running on SQLite."""
    if current_app.config["DATABASE_ENGINE"] == "sqlite":
        return sql.replace("%s", "?")
    return sql


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """Run a SELECT and return every row as a dict."""
    cursor = require_db().cursor()
    cursor.execute(prepare_sql(sql), params)
    return list(cursor.fetchall())


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Run a SELECT and return the first row as a dict, or None."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple = ()) -> int:
    """Run one INSERT/UPDATE/DELETE, commit, and return the new row id (if any)."""
    db = require_db()
    cursor = db.cursor()
    try:
        cursor.execute(prepare_sql(sql), params)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return cursor.lastrowid


def execute_all(statements: list[tuple[str, tuple]]) -> None:
    """Run several write statements as one transaction: all commit or none do."""
    db = require_db()
    cursor = db.cursor()
    try:
        for sql, params in statements:
            cursor.execute(prepare_sql(sql), params)
        db.commit()
    except Exception:
        db.rollback()
        raise
