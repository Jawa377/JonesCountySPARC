"""Site-wide helpers shared by every blueprint.

- Current teacher: get_current_teacher() / set_current_teacher() / teacher_required.
  Phase 1 has no login; the teacher picked on /teacher/ is kept in the Flask
  session. Real auth later replaces these three functions and nothing else.
- Ownership: get_owned_unit() so no screen ever shows another teacher's unit.
- Coverage: get_unit_coverage(), the Standards Engine rollup used by the
  studio rail, the unit page, and the coverage panel.
"""

from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for

from app.db_connect import query_all, query_one
from app.services.standards_retrieval import retrieve_standards

SESSION_TEACHER_KEY = "teacher_id"

VOICE_LABELS = {"match_materials": "Match my materials"}

STATUS_RANK = {"covered": 0, "partial": 1, "gap": 2}

# Which studio tab shows each kind of alignable element.
ELEMENT_TABS = {"section": "section", "assignment": "assignments", "quiz_item": "quiz"}

EDITED_OUT_NOTE = "The evidence passage was edited out of the text"


# --- Current teacher -------------------------------------------------------

def get_current_teacher() -> dict | None:
    """Return the current teacher (teacher_id, name, email), or None.

    Reads teacher_id from the session and caches the row on flask.g for the
    rest of the request. A session id that no longer matches a teacher is
    cleared.
    """
    if "current_teacher" in g:
        return g.current_teacher
    teacher = None
    teacher_id = session.get(SESSION_TEACHER_KEY)
    if teacher_id is not None:
        teacher = query_one(
            "SELECT teacher_id, name, email FROM teachers WHERE teacher_id = %s",
            (teacher_id,),
        )
        if teacher is None:
            session.pop(SESSION_TEACHER_KEY, None)
    g.current_teacher = teacher
    return teacher


def set_current_teacher(teacher_id: int) -> None:
    """Make teacher_id the current teacher for this browser session."""
    session[SESSION_TEACHER_KEY] = teacher_id
    g.pop("current_teacher", None)


def teacher_required(view):
    """Route decorator: send the visitor to the teacher picker if nobody is picked."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_current_teacher() is None:
            flash("Choose your name to continue.", "info")
            return redirect(url_for("teachers.list_teachers"))
        return view(*args, **kwargs)
    return wrapped


# --- Ownership and shared reads --------------------------------------------

def get_owned_unit(unit_id: int) -> dict:
    """Return the unit if the current teacher owns it; otherwise abort with 404.

    404 (not 403) so one teacher can't learn which unit ids exist for others.
    """
    unit = query_one(
        "SELECT unit_id, teacher_id, subject, grade, unit_number, title, standards_set, "
        "lexile_min, lexile_max, voice FROM units WHERE unit_id = %s AND teacher_id = %s",
        (unit_id, get_current_teacher()["teacher_id"]),
    )
    if unit is None:
        abort(404)
    return unit


def get_unit_materials(unit_id: int) -> list[dict]:
    """Return a unit's material records, oldest first."""
    return query_all(
        "SELECT material_id, filename, file_type, size_label, uploaded_at "
        "FROM materials WHERE unit_id = %s ORDER BY material_id",
        (unit_id,),
    )


def count_words(body_text: str) -> int:
    """Count words in section body text, ignoring "## " subheading markers."""
    return len(body_text.replace("## ", " ").split())


def safe_next_url(default: str) -> str:
    """Return the form's "next" path if it's a local path, else default.

    Only same-site paths ("/studio/...") are allowed, never "//host" or
    full URLs, so forms can't be used to redirect off-site.
    """
    target = request.form.get("next", "")
    if target.startswith("/") and not target.startswith("//"):
        return target
    return default


# --- Coverage (Standards Engine rollup) ------------------------------------

def load_element_texts(unit_id: int) -> dict[tuple[str, int], dict]:
    """Return every alignable element in a unit, keyed by (element_type, element_id).

    Each value has the element's text (section body or item prompt) and the
    section_id it lives in, so the UI can link evidence back to the studio.
    """
    elements = {}
    for row in query_all(
        "SELECT section_id, body_text FROM sections WHERE unit_id = %s", (unit_id,)
    ):
        elements[("section", row["section_id"])] = {"text": row["body_text"], "section_id": row["section_id"]}
    for row in query_all(
        "SELECT a.assignment_id, a.section_id, a.prompt_text FROM assignments a "
        "JOIN sections s ON s.section_id = a.section_id WHERE s.unit_id = %s",
        (unit_id,),
    ):
        elements[("assignment", row["assignment_id"])] = {"text": row["prompt_text"], "section_id": row["section_id"]}
    for row in query_all(
        "SELECT q.quiz_item_id, q.section_id, q.prompt_text FROM quiz_items q "
        "JOIN sections s ON s.section_id = q.section_id WHERE s.unit_id = %s",
        (unit_id,),
    ):
        elements[("quiz_item", row["quiz_item_id"])] = {"text": row["prompt_text"], "section_id": row["section_id"]}
    return elements


def check_evidence(alignment: dict, elements: dict) -> dict | None:
    """Return the alignment's evidence (with section_id) if it still holds, else None.

    Evidence holds when the element still exists and, if the alignment names
    an exact passage, that passage is still in the element's text word for
    word. This is what keeps coverage honest after a teacher edits.
    """
    element = elements.get((alignment["element_type"], alignment["element_id"]))
    if element is None:
        return None
    if alignment["evidence_text"] and alignment["evidence_text"] not in element["text"]:
        return None
    return {
        "alignment_id": alignment["alignment_id"],
        "element_type": alignment["element_type"],
        "element_id": alignment["element_id"],
        "section_id": element["section_id"],
        "tab": ELEMENT_TABS[alignment["element_type"]],
        "coverage_status": alignment["coverage_status"],
        "evidence_text": alignment["evidence_text"],
        "evidence_note": alignment["evidence_note"],
    }


def rollup_standard(standard: dict, alignments: list[dict], elements: dict, dismissal: dict | None) -> dict:
    """Return one standard's coverage card: status, note, evidence, dismissal.

    Status: any valid covered row -> covered; else any valid partial row ->
    partial; else gap. A gap's note comes from its gap row, or explains that
    evidence was edited out. A dismissal only applies while the standard is a gap.
    """
    evidence = [e for e in (check_evidence(a, elements) for a in alignments if a["coverage_status"] != "gap") if e]
    covered = [e for e in evidence if e["coverage_status"] == "covered"]
    partial = [e for e in evidence if e["coverage_status"] == "partial"]
    gap_rows = [a for a in alignments if a["coverage_status"] == "gap"]

    if covered:
        status, note = "covered", None
    elif partial:
        status, note = "partial", partial[0]["evidence_note"]
    else:
        status = "gap"
        if gap_rows:
            note = gap_rows[0]["evidence_note"]
        elif alignments:
            note = EDITED_OUT_NOTE
        else:
            note = "Nothing covers it"

    return {
        **standard,
        "status": status,
        "note": note,
        "evidence": covered + partial,
        "dismissal": dismissal if status == "gap" else None,
    }


def get_unit_coverage(unit: dict) -> dict:
    """Return the Standards Engine view of a unit.

    Output: {
      "standards": [card, ...]  covered first, then partial, then gap, by code,
      "total": number of standards in the unit's set,
      "addressed": covered + partial (the "3" in "3 / 5"),
      "counts": {"covered", "partial", "gap", "dismissed"}  (gap excludes dismissed)
    }
    Only standards returned by retrieve_standards() appear; alignments that
    point at any other standard are ignored.
    """
    standards = retrieve_standards(unit["standards_set"])
    alignments = query_all(
        "SELECT alignment_id, standard_id, element_type, element_id, coverage_status, "
        "evidence_text, evidence_note FROM alignments WHERE unit_id = %s ORDER BY alignment_id",
        (unit["unit_id"],),
    )
    dismissals = {
        row["standard_id"]: row
        for row in query_all(
            "SELECT dismissal_id, standard_id, reason, dismissed_at FROM coverage_dismissals WHERE unit_id = %s",
            (unit["unit_id"],),
        )
    }
    elements = load_element_texts(unit["unit_id"])

    cards = [
        rollup_standard(
            standard,
            [a for a in alignments if a["standard_id"] == standard["standard_id"]],
            elements,
            dismissals.get(standard["standard_id"]),
        )
        for standard in standards
    ]
    cards.sort(key=lambda card: (STATUS_RANK[card["status"]], card["code"]))

    dismissed = sum(1 for card in cards if card["dismissal"])
    counts = {
        "covered": sum(1 for card in cards if card["status"] == "covered"),
        "partial": sum(1 for card in cards if card["status"] == "partial"),
        "gap": sum(1 for card in cards if card["status"] == "gap") - dismissed,
        "dismissed": dismissed,
    }
    return {
        "standards": cards,
        "total": len(cards),
        "addressed": counts["covered"] + counts["partial"],
        "counts": counts,
    }
