"""Units blueprint: the current teacher's units and a single unit's overview."""

from flask import Blueprint, render_template

from app.db_connect import query_all
from app.functions import (
    VOICE_LABELS,
    get_current_teacher,
    get_owned_unit,
    get_unit_coverage,
    get_unit_materials,
    teacher_required,
)

bp = Blueprint("units", __name__)


@bp.get("/")
@teacher_required
def list_units():
    """List the current teacher's units with section and material counts."""
    units = query_all(
        "SELECT u.unit_id, u.subject, u.grade, u.unit_number, u.title, u.standards_set, "
        "(SELECT COUNT(*) FROM sections s WHERE s.unit_id = u.unit_id) AS section_count, "
        "(SELECT COUNT(*) FROM materials m WHERE m.unit_id = u.unit_id) AS material_count "
        "FROM units u WHERE u.teacher_id = %s ORDER BY u.subject, u.grade, u.unit_number",
        (get_current_teacher()["teacher_id"],),
    )
    return render_template("units.html", units=units)


@bp.get("/<int:unit_id>")
@teacher_required
def view_unit(unit_id: int):
    """Show one unit: its sections, materials, draft settings, and coverage summary."""
    unit = get_owned_unit(unit_id)
    sections = query_all(
        "SELECT section_id, section_number, title, word_count, lexile, status "
        "FROM sections WHERE unit_id = %s ORDER BY section_number",
        (unit_id,),
    )
    return render_template(
        "unit.html",
        unit=unit,
        sections=sections,
        materials=get_unit_materials(unit_id),
        coverage=get_unit_coverage(unit),
        voice_label=VOICE_LABELS.get(unit["voice"], unit["voice"]),
    )
