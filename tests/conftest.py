"""Shared pytest fixtures.

Each test gets its own SQLite file built from database/schema.sql and
seed_data.sql, so tests use the real SQL and seed data without touching
database/sparc.db or needing a network database.
"""

import os
import sqlite3
from pathlib import Path

import pytest

# app/__init__.py builds an app at import time, which requires a secret key.
os.environ.setdefault("FLASK_SECRET_KEY", "test-only-secret")

from app.app_factory import create_app  # noqa: E402

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
RUFFIN_ID = 1
PLACEHOLDER_ID = 2


@pytest.fixture
def db_path(tmp_path):
    """Path to a freshly built and seeded SQLite database."""
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    for name in ("schema.sql", "seed_data.sql"):
        conn.executescript((DATABASE_DIR / name).read_text(encoding="utf-8"))
    conn.close()
    return path


@pytest.fixture
def app(db_path):
    """App wired to the test database."""
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "DATABASE_ENGINE": "sqlite",
        "SQLITE_PATH": str(db_path),
    })


@pytest.fixture
def client(app):
    """Test client with no teacher picked."""
    return app.test_client()


def act_as(client, teacher_id):
    """Make teacher_id the current teacher for this client's session."""
    with client.session_transaction() as session:
        session["teacher_id"] = teacher_id
    return client


@pytest.fixture
def ruffin(client):
    """Test client working as Ms. Ruffin (owner of Unit 3)."""
    return act_as(client, RUFFIN_ID)


@pytest.fixture
def other_teacher(client):
    """Test client working as a placeholder teacher with no units."""
    return act_as(client, PLACEHOLDER_ID)


@pytest.fixture
def db(db_path):
    """Direct connection to the test database for asserting on rows."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
