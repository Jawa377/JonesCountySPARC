"""Standards Engine tests: rollup, honesty after edits, dismissals."""

from app.functions import get_unit_coverage


def coverage_for(app, client):
    """Compute Unit 3 coverage inside a request as Ms. Ruffin."""
    with app.test_request_context():
        from flask import session
        session["teacher_id"] = 1
        unit = {"unit_id": 1, "standards_set": "GSE Science Grade 6"}
        return get_unit_coverage(unit)


def statuses(coverage):
    return {card["code"]: card["status"] for card in coverage["standards"]}


def test_seed_rollup_matches_handout(app, ruffin):
    coverage = coverage_for(app, ruffin)
    assert statuses(coverage) == {
        "S6E3.a": "covered", "S6E4.b": "covered", "S6E3.c": "partial", "S6E3.b": "gap", "S6E3.d": "gap",
    }
    assert [card["code"] for card in coverage["standards"]] == ["S6E3.a", "S6E4.b", "S6E3.c", "S6E3.b", "S6E3.d"]
    assert (coverage["addressed"], coverage["total"]) == (3, 5)
    notes = {card["code"]: card["note"] for card in coverage["standards"]}
    assert notes["S6E3.c"] == "Explains runoff, but no item asks for a solution"
    assert notes["S6E3.b"] == "Nothing covers it"
    assert notes["S6E3.d"] == "Planned for Section 2"


def test_editing_out_evidence_downgrades_coverage(app, ruffin):
    """Removing the only S6E3.a passage must turn S6E3.a into a gap, not leave it 'covered'."""
    body = "Water is stubborn about changing temperature. Sand, rock, and soil do the opposite — they heat fast and cool fast. That single difference explains why a beach burns your feet at noon while the ocean twenty steps away is still cold."
    ruffin.post("/studio/section/edit/1", data={"title": "Why Water Runs the Planet", "body_text": body})
    coverage = coverage_for(app, ruffin)
    card = next(c for c in coverage["standards"] if c["code"] == "S6E3.a")
    assert card["status"] == "gap"
    assert "edited out" in card["note"]
    assert statuses(coverage)["S6E4.b"] == "covered"


def test_coverage_page_and_detail_200(ruffin):
    assert ruffin.get("/standard/unit/1").status_code == 200
    detail = ruffin.get("/standard/5/unit/1").data.decode()
    assert "S6E4.b" in detail
    assert "Water is stubborn about changing temperature" in detail


def test_unknown_standard_is_404(ruffin):
    assert ruffin.get("/standard/999/unit/1").status_code == 404


def test_dismiss_gap_then_undo(ruffin, db):
    resp = ruffin.post("/standard/dismiss", data={"unit_id": 1, "standard_id": 4, "reason": "Planned for Section 2"})
    assert resp.status_code == 302
    assert db.execute("SELECT COUNT(*) FROM coverage_dismissals").fetchone()[0] == 1
    assert "1 dismissed" in ruffin.get("/studio/section/1").data.decode()

    ruffin.post("/standard/dismiss", data={"unit_id": 1, "standard_id": 4, "reason": "again"})
    assert db.execute("SELECT COUNT(*) FROM coverage_dismissals").fetchone()[0] == 1

    ruffin.post("/standard/undismiss", data={"unit_id": 1, "standard_id": 4})
    assert db.execute("SELECT COUNT(*) FROM coverage_dismissals").fetchone()[0] == 0


def test_cannot_dismiss_covered_standard(ruffin, db):
    ruffin.post("/standard/dismiss", data={"unit_id": 1, "standard_id": 5, "reason": "nope"})
    assert db.execute("SELECT COUNT(*) FROM coverage_dismissals").fetchone()[0] == 0


def test_dismiss_redirect_stays_on_site(ruffin):
    resp = ruffin.post("/standard/dismiss", data={"unit_id": 1, "standard_id": 2, "next": "//evil.example"})
    assert resp.headers["Location"].endswith("/standard/unit/1")
