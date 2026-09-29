"""Studio screen and edit tests."""


def test_open_unit_redirects_to_first_section(ruffin):
    resp = ruffin.get("/studio/unit/1")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/studio/section/1?tab=section")


def test_studio_200_shows_draft_and_rail(ruffin):
    resp = ruffin.get("/studio/section/1")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Why Water Runs the Planet" in body
    assert "Generated from your 5 files · 1,180 words · Lexile 910" in body
    assert "3 / 5" in body
    assert "Draft generated · 2 covered, 1 partial, 2 gaps" in body


def test_studio_tabs_show_section_items(ruffin):
    assignments = ruffin.get("/studio/section/2?tab=assignments").data.decode()
    assert "two-pan data table" in assignments
    quiz = ruffin.get("/studio/section/2?tab=quiz").data.decode()
    assert "100 mL of water" in quiz


def test_edit_section_saves_and_recounts(ruffin, db):
    resp = ruffin.post("/studio/section/edit/2", data={"title": "Why the Coast Stays Mild", "body_text": "One two three.\r\n\r\n## Four\r\n\r\nFive six."})
    assert resp.status_code == 302
    row = db.execute("SELECT body_text, word_count, status FROM sections WHERE section_id = 2").fetchone()
    assert row["word_count"] == 6
    assert row["status"] == "edited"
    assert "\r" not in row["body_text"]


def test_edit_section_rejects_empty_body(ruffin, db):
    ruffin.post("/studio/section/edit/1", data={"title": "T", "body_text": "   "})
    assert db.execute("SELECT status FROM sections WHERE section_id = 1").fetchone()["status"] == "draft"


def test_edit_assignment(ruffin, db):
    resp = ruffin.post("/studio/assignment/edit/1", data={"prompt_text": "New support prompt."})
    assert resp.headers["Location"].endswith("/studio/section/2?tab=assignments")
    assert db.execute("SELECT prompt_text FROM assignments WHERE assignment_id = 1").fetchone()[0] == "New support prompt."


def test_edit_quiz_item_validates_dok(ruffin, db):
    ruffin.post("/studio/quiz_item/edit/1", data={"prompt_text": "Q", "dok_level": 7})
    assert db.execute("SELECT dok_level FROM quiz_items WHERE quiz_item_id = 1").fetchone()[0] == 3
    ruffin.post("/studio/quiz_item/edit/1", data={"prompt_text": "Q", "dok_level": 2})
    assert db.execute("SELECT dok_level FROM quiz_items WHERE quiz_item_id = 1").fetchone()[0] == 2


def test_edit_settings(ruffin, db):
    ruffin.post("/studio/unit/settings/1", data={"lexile_min": 800, "lexile_max": 900, "voice": "match_materials", "section_id": 1})
    row = db.execute("SELECT lexile_min, lexile_max FROM units WHERE unit_id = 1").fetchone()
    assert (row[0], row[1]) == (800, 900)


def test_edit_settings_rejects_inverted_range(ruffin, db):
    ruffin.post("/studio/unit/settings/1", data={"lexile_min": 950, "lexile_max": 850, "voice": "match_materials"})
    assert db.execute("SELECT lexile_min FROM units WHERE unit_id = 1").fetchone()[0] == 850
