"""Units blueprint tests."""


def test_list_units_200(ruffin):
    resp = ruffin.get("/unit/")
    assert resp.status_code == 200
    assert b"Water in Earth&#39;s Systems" in resp.data
    assert b"6th Grade Science" in resp.data


def test_placeholder_teacher_has_no_units(other_teacher):
    resp = other_teacher.get("/unit/")
    assert resp.status_code == 200
    assert b"any units yet" in resp.data


def test_view_unit_200(ruffin):
    resp = ruffin.get("/unit/1")
    assert resp.status_code == 200
    assert b"Why Water Runs the Planet" in resp.data
    assert b"Why the Coast Stays Mild" in resp.data
    assert b"2 covered, 1 partial, 2 gaps" in resp.data
