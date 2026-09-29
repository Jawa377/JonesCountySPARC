"""Studios blueprint: the authoring screen (handout page 2), its edit forms,
and the lesson view (handout page 3).

The studio shows one section at a time: materials on the left, the section
with Textbook / Assignments / Quiz tabs in the center, and the unit's
standards coverage rail on the right. Every edit is a POST that redirects
back to the same tab. The lesson view renders the same section record as a
finished textbook page.
"""

import re

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.db_connect import execute, query_all, query_one
from app.functions import (
    VOICE_LABELS,
    count_words,
    get_current_teacher,
    get_owned_unit,
    get_unit_coverage,
    get_unit_materials,
    teacher_required,
)

bp = Blueprint("studios", __name__)

TABS = ("section", "assignments", "quiz")
LEXILE_RANGE = (0, 2000)
MAX_TITLE_LENGTH = 200


def get_owned_section(section_id: int) -> dict:
    """Return a section the current teacher owns (joined to its unit), or abort 404."""
    section = query_one(
        "SELECT s.section_id, s.unit_id, s.section_number, s.title, s.learning_target, s.body_text, "
        "s.word_count, s.lexile, s.duration_minutes, s.status "
        "FROM sections s JOIN units u ON u.unit_id = s.unit_id "
        "WHERE s.section_id = %s AND u.teacher_id = %s",
        (section_id, get_current_teacher()["teacher_id"]),
    )
    if section is None:
        abort(404)
    return section


def get_section_assignments(section_id: int) -> list[dict]:
    """Return a section's assignments in support, core, extension order."""
    return query_all(
        "SELECT assignment_id, level, prompt_text FROM assignments WHERE section_id = %s "
        "ORDER BY CASE level WHEN 'support' THEN 1 WHEN 'core' THEN 2 ELSE 3 END, assignment_id",
        (section_id,),
    )


def get_section_quiz_items(section_id: int) -> list[dict]:
    """Return a section's quiz items in the order they were created."""
    return query_all(
        "SELECT quiz_item_id, dok_level, prompt_text FROM quiz_items WHERE section_id = %s ORDER BY quiz_item_id",
        (section_id,),
    )


def get_owned_item(table: str, id_column: str, item_id: int) -> dict:
    """Return an assignment or quiz item row plus its section_id, if the teacher owns it.

    table/id_column are fixed strings from this module, never user input.
    """
    item = query_one(
        f"SELECT i.{id_column}, i.section_id FROM {table} i "
        "JOIN sections s ON s.section_id = i.section_id "
        "JOIN units u ON u.unit_id = s.unit_id "
        f"WHERE i.{id_column} = %s AND u.teacher_id = %s",
        (item_id, get_current_teacher()["teacher_id"]),
    )
    if item is None:
        abort(404)
    return item


def mark_passages(text: str, passages: list[tuple[str, str]]) -> list[dict]:
    """Split a paragraph into segments, tagging the ones inside evidence passages.

    Input:  paragraph text; (standard code, exact passage) pairs.
    Output: [{"text": str, "codes": [codes covering this segment]}] in order.
    Overlapping passages are fine: each segment lists every code covering it.
    """
    spans = []
    for code, passage in passages:
        start = text.find(passage) if passage else -1
        if start >= 0:
            spans.append((start, start + len(passage), code))
    cuts = sorted({0, len(text), *(s for s, _, _ in spans), *(e for _, e, _ in spans)})
    return [
        {"text": text[a:b], "codes": sorted({code for s, e, code in spans if s <= a and b <= e})}
        for a, b in zip(cuts, cuts[1:])
    ]


def build_blocks(body_text: str, passages: list[tuple[str, str]]) -> list[dict]:
    """Turn section body text into headings and paragraphs for display.

    Paragraphs are separated by blank lines; a line starting with "## " is a
    subheading. Output: [{"kind": "heading"|"paragraph", "text"|"segments"}].
    """
    blocks = []
    for chunk in re.split(r"\n\s*\n", body_text.strip()):
        chunk = chunk.strip()
        if chunk.startswith("## "):
            heading, _, rest = chunk.partition("\n")
            blocks.append({"kind": "heading", "text": heading[3:].strip()})
            chunk = rest.strip()
        if chunk:
            blocks.append({"kind": "paragraph", "segments": mark_passages(chunk, passages)})
    return blocks


def section_evidence(coverage: dict, section_id: int) -> dict:
    """Pull one section's evidence out of the unit coverage.

    Output: {
      "passages": [(code, exact passage)] inside the section body,
      "item_codes": {"assignment-1": [codes], "quiz_item-1": [codes]},
      "codes": codes with any evidence in this section, in rail order,
    }
    """
    passages, item_codes, codes = [], {}, []
    for card in coverage["standards"]:
        for evidence in card["evidence"]:
            if evidence["section_id"] != section_id:
                continue
            if card["code"] not in codes:
                codes.append(card["code"])
            if evidence["element_type"] == "section":
                if evidence["evidence_text"]:
                    passages.append((card["code"], evidence["evidence_text"]))
            else:
                key = f"{evidence['element_type']}-{evidence['element_id']}"
                item_codes.setdefault(key, []).append(card["code"])
    return {"passages": passages, "item_codes": item_codes, "codes": codes}


def studio_url(section_id: int, tab: str = "section") -> str:
    """URL of the studio screen for a section, on a given tab."""
    return url_for("studios.show_studio", section_id=section_id, tab=tab)


@bp.get("/unit/<int:unit_id>")
@teacher_required
def open_unit(unit_id: int):
    """Open the studio on a unit's first section."""
    get_owned_unit(unit_id)
    first = query_one(
        "SELECT section_id FROM sections WHERE unit_id = %s ORDER BY section_number", (unit_id,)
    )
    if first is None:
        flash("This unit has no sections yet.", "info")
        return redirect(url_for("units.view_unit", unit_id=unit_id))
    return redirect(studio_url(first["section_id"]))


@bp.get("/section/<int:section_id>")
@teacher_required
def show_studio(section_id: int):
    """The three-column authoring screen for one section."""
    section = get_owned_section(section_id)
    unit = get_owned_unit(section["unit_id"])
    tab = request.args.get("tab", "section")
    if tab not in TABS:
        tab = "section"

    sections = query_all(
        "SELECT section_id, section_number, title FROM sections WHERE unit_id = %s ORDER BY section_number",
        (unit["unit_id"],),
    )
    coverage = get_unit_coverage(unit)
    evidence = section_evidence(coverage, section_id)
    return render_template(
        "studio.html",
        unit=unit,
        section=section,
        sections=sections,
        tab=tab,
        materials=get_unit_materials(unit["unit_id"]),
        assignments=get_section_assignments(section_id),
        quiz_items=get_section_quiz_items(section_id),
        coverage=coverage,
        blocks=build_blocks(section["body_text"], evidence["passages"]),
        item_codes=evidence["item_codes"],
        voice_labels=VOICE_LABELS,
    )


@bp.get("/lesson/<int:section_id>")
@teacher_required
def show_lesson(section_id: int):
    """One section rendered as a finished lesson page (handout page 3)."""
    section = get_owned_section(section_id)
    unit = get_owned_unit(section["unit_id"])
    coverage = get_unit_coverage(unit)
    evidence = section_evidence(coverage, section_id)
    assignments = get_section_assignments(section_id)

    practice_codes = {tuple(evidence["item_codes"].get(f"assignment-{a['assignment_id']}", [])) for a in assignments}
    return render_template(
        "lesson.html",
        unit=unit,
        section=section,
        blocks=build_blocks(section["body_text"], []),
        vocab=query_all(
            "SELECT term, definition FROM vocab_terms WHERE section_id = %s ORDER BY sort_order, vocab_term_id",
            (section_id,),
        ),
        assignments=assignments,
        quiz_items=get_section_quiz_items(section_id),
        item_codes=evidence["item_codes"],
        standards_here=[card for card in coverage["standards"] if card["code"] in evidence["codes"]],
        same_standard=len(assignments) > 1 and len(practice_codes) == 1 and () not in practice_codes,
    )


@bp.post("/section/edit/<int:section_id>")
@teacher_required
def edit_section(section_id: int):
    """Save the section's title and body; recount words and mark it edited."""
    section = get_owned_section(section_id)
    title = request.form.get("title", "").strip()
    body_text = request.form.get("body_text", "").replace("\r\n", "\n").strip()

    if not title or not body_text:
        flash("A section needs both a title and body text.", "error")
        return redirect(studio_url(section_id))
    if len(title) > MAX_TITLE_LENGTH:
        flash(f"Titles are limited to {MAX_TITLE_LENGTH} characters.", "error")
        return redirect(studio_url(section_id))

    execute(
        "UPDATE sections SET title = %s, body_text = %s, word_count = %s, status = 'edited', "
        "updated_at = CURRENT_TIMESTAMP WHERE section_id = %s",
        (title, body_text, count_words(body_text), section["section_id"]),
    )
    flash("Section saved.", "success")
    return redirect(studio_url(section_id))


@bp.post("/assignment/edit/<int:assignment_id>")
@teacher_required
def edit_assignment(assignment_id: int):
    """Save one assignment's prompt text."""
    item = get_owned_item("assignments", "assignment_id", assignment_id)
    prompt_text = request.form.get("prompt_text", "").strip()
    if not prompt_text:
        flash("An assignment can't be empty.", "error")
        return redirect(studio_url(item["section_id"], "assignments"))

    execute("UPDATE assignments SET prompt_text = %s WHERE assignment_id = %s", (prompt_text, assignment_id))
    flash("Assignment saved.", "success")
    return redirect(studio_url(item["section_id"], "assignments"))


@bp.post("/quiz_item/edit/<int:quiz_item_id>")
@teacher_required
def edit_quiz_item(quiz_item_id: int):
    """Save one quiz item's prompt text and DOK level (1-4)."""
    item = get_owned_item("quiz_items", "quiz_item_id", quiz_item_id)
    prompt_text = request.form.get("prompt_text", "").strip()
    dok_level = request.form.get("dok_level", type=int)
    if not prompt_text or dok_level not in (1, 2, 3, 4):
        flash("A quiz item needs text and a DOK level from 1 to 4.", "error")
        return redirect(studio_url(item["section_id"], "quiz"))

    execute(
        "UPDATE quiz_items SET prompt_text = %s, dok_level = %s WHERE quiz_item_id = %s",
        (prompt_text, dok_level, quiz_item_id),
    )
    flash("Quiz item saved.", "success")
    return redirect(studio_url(item["section_id"], "quiz"))


@bp.post("/unit/settings/<int:unit_id>")
@teacher_required
def edit_settings(unit_id: int):
    """Save a unit's draft settings: Lexile range and voice.

    The standards set is read-only here: changing it would orphan every
    alignment in the unit.
    """
    unit = get_owned_unit(unit_id)
    back = request.form.get("section_id", type=int)
    back_url = studio_url(back) if back else url_for("units.view_unit", unit_id=unit_id)

    lexile_min = request.form.get("lexile_min", type=int)
    lexile_max = request.form.get("lexile_max", type=int)
    voice = request.form.get("voice", "")
    low, high = LEXILE_RANGE
    if lexile_min is None or lexile_max is None or not (low <= lexile_min <= lexile_max <= high):
        flash(f"Reading level needs two numbers from {low} to {high}, low first.", "error")
        return redirect(back_url)
    if voice not in VOICE_LABELS:
        flash("Pick a voice from the list.", "error")
        return redirect(back_url)

    execute(
        "UPDATE units SET lexile_min = %s, lexile_max = %s, voice = %s, updated_at = CURRENT_TIMESTAMP "
        "WHERE unit_id = %s",
        (lexile_min, lexile_max, voice, unit["unit_id"]),
    )
    flash("Draft settings saved.", "success")
    return redirect(back_url)
