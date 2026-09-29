"""Standards blueprint: the coverage panel, a standard's evidence, and dismissing gaps.

Coverage is computed by get_unit_coverage() (app/functions.py); standards
themselves only ever come from retrieve_standards() (app/services).
"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.db_connect import INTEGRITY_ERRORS, execute
from app.functions import get_owned_unit, get_unit_coverage, safe_next_url, teacher_required

bp = Blueprint("standards", __name__)

MAX_REASON_LENGTH = 255


def find_card(coverage: dict, standard_id: int) -> dict:
    """Return the coverage card for standard_id, or abort 404 if it isn't in the unit's set."""
    for card in coverage["standards"]:
        if card["standard_id"] == standard_id:
            return card
    abort(404)


@bp.get("/unit/<int:unit_id>")
@teacher_required
def show_coverage(unit_id: int):
    """Full coverage panel for a unit: every standard with its status."""
    unit = get_owned_unit(unit_id)
    return render_template("standards.html", unit=unit, coverage=get_unit_coverage(unit))


@bp.get("/<int:standard_id>/unit/<int:unit_id>")
@teacher_required
def show_standard(standard_id: int, unit_id: int):
    """One standard in one unit: description, source, and every evidence passage."""
    unit = get_owned_unit(unit_id)
    card = find_card(get_unit_coverage(unit), standard_id)
    return render_template("standard.html", unit=unit, card=card)


@bp.post("/dismiss")
@teacher_required
def dismiss_gap():
    """Mark a gap as intentional (e.g. "Planned for Section 2"). Gaps only."""
    unit = get_owned_unit(request.form.get("unit_id", type=int) or 0)
    card = find_card(get_unit_coverage(unit), request.form.get("standard_id", type=int) or 0)
    back = safe_next_url(url_for("standards.show_coverage", unit_id=unit["unit_id"]))

    if card["status"] != "gap":
        flash(f"{card['code']} isn't a gap, so there's nothing to dismiss.", "error")
        return redirect(back)
    reason = request.form.get("reason", "").strip()[:MAX_REASON_LENGTH] or card["note"] or "Dismissed"

    try:
        execute(
            "INSERT INTO coverage_dismissals (unit_id, standard_id, reason) VALUES (%s, %s, %s)",
            (unit["unit_id"], card["standard_id"], reason),
        )
    except INTEGRITY_ERRORS:
        flash(f"{card['code']} is already dismissed.", "info")
        return redirect(back)
    flash(f"Dismissed {card['code']}: {reason}", "success")
    return redirect(back)


@bp.post("/undismiss")
@teacher_required
def undismiss_gap():
    """Put a dismissed gap back into the gap count."""
    unit = get_owned_unit(request.form.get("unit_id", type=int) or 0)
    card = find_card(get_unit_coverage(unit), request.form.get("standard_id", type=int) or 0)

    execute(
        "DELETE FROM coverage_dismissals WHERE unit_id = %s AND standard_id = %s",
        (unit["unit_id"], card["standard_id"]),
    )
    flash(f"{card['code']} is back in the gap count.", "success")
    return redirect(safe_next_url(url_for("standards.show_coverage", unit_id=unit["unit_id"])))
