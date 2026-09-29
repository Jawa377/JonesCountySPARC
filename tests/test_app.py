"""App factory, teacher picker, and access-control tests."""

import pytest

from app.app_factory import create_app


def test_missing_secret_key_refuses_to_start(monkeypatch):
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="FLASK_SECRET_KEY"):
        create_app({"SECRET_KEY": None})


def test_home_without_teacher_goes_to_picker(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/teacher/")


def test_picker_lists_teachers(client):
    resp = client.get("/teacher/")
    assert resp.status_code == 200
    assert b"Ms. Ruffin" in resp.data


def test_select_teacher_sets_session_and_redirects(client):
    resp = client.post("/teacher/select", data={"teacher_id": 1})
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/unit/")
    with client.session_transaction() as session:
        assert session["teacher_id"] == 1


def test_select_unknown_teacher_is_rejected(client):
    resp = client.post("/teacher/select", data={"teacher_id": 999})
    assert resp.headers["Location"].endswith("/teacher/")
    with client.session_transaction() as session:
        assert "teacher_id" not in session


@pytest.mark.parametrize("path", ["/unit/", "/unit/1", "/studio/section/1", "/standard/unit/1", "/material/unit/1"])
def test_pages_require_a_teacher(client, path):
    resp = client.get(path)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/teacher/")


@pytest.mark.parametrize("path", ["/unit/1", "/studio/section/1", "/standard/unit/1", "/material/unit/1", "/standard/5/unit/1"])
def test_other_teachers_units_are_404(other_teacher, path):
    assert other_teacher.get(path).status_code == 404


def test_other_teacher_cannot_edit_ruffins_section(other_teacher, db):
    resp = other_teacher.post("/studio/section/edit/1", data={"title": "Hijacked", "body_text": "x"})
    assert resp.status_code == 404
    assert db.execute("SELECT title FROM sections WHERE section_id = 1").fetchone()["title"] == "Why Water Runs the Planet"


def test_database_unavailable_returns_503(db_path, tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "SQLITE_PATH": str(tmp_path / "missing.db")})
    client = app.test_client()
    with client.session_transaction() as session:
        session["teacher_id"] = 1
    resp = client.get("/unit/")
    assert resp.status_code == 503
    assert b"Database unavailable" in resp.data
    assert not (tmp_path / "missing.db").exists()
