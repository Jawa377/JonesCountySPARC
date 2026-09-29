"""Materials blueprint tests."""

import io


def upload(client, name, size=2048, **extra):
    data = {"unit_id": 1, "file": (io.BytesIO(b"x" * size), name), **extra}
    return client.post("/material/add", data=data, content_type="multipart/form-data")


def test_list_materials_200(ruffin):
    resp = ruffin.get("/material/unit/1")
    assert resp.status_code == 200
    assert b"Ocmulgee Lab" in resp.data
    assert b"18 slides" in resp.data


def test_upload_records_name_type_size(ruffin, db):
    resp = upload(ruffin, "Groundwater Notes.docx", size=300 * 1024)
    assert resp.status_code == 302
    row = db.execute("SELECT filename, file_type, size_label FROM materials ORDER BY material_id DESC").fetchone()
    assert tuple(row) == ("Groundwater Notes", "DOCX", "300 KB")


def test_upload_rejects_other_types(ruffin, db):
    upload(ruffin, "notes.txt")
    assert db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 5


def test_upload_can_return_to_studio(ruffin):
    resp = upload(ruffin, "Lab.pdf", next="/studio/section/1")
    assert resp.headers["Location"].endswith("/studio/section/1")


def test_delete_material(ruffin, db):
    resp = ruffin.post("/material/delete/5")
    assert resp.status_code == 302
    assert db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 4


def test_other_teacher_cannot_delete(other_teacher, db):
    assert other_teacher.post("/material/delete/5").status_code == 404
    assert db.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 5
