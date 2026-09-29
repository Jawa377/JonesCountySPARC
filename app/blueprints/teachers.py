"""Teachers blueprint: the Phase 1 "who are you?" picker.

There is no login in Phase 1. Picking a teacher stores their id in the
session via set_current_teacher(); every other screen then shows only
that teacher's units.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.db_connect import query_all, query_one
from app.functions import set_current_teacher

bp = Blueprint("teachers", __name__)


@bp.get("/")
def list_teachers():
    """Show every pilot teacher so the visitor can pick who they are."""
    teachers = query_all("SELECT teacher_id, name, email FROM teachers ORDER BY teacher_id")
    return render_template("teachers.html", teachers=teachers)


@bp.post("/select")
def select_teacher():
    """Make the chosen teacher current, then go to their units."""
    teacher_id = request.form.get("teacher_id", type=int)
    teacher = None
    if teacher_id is not None:
        teacher = query_one("SELECT teacher_id, name FROM teachers WHERE teacher_id = %s", (teacher_id,))
    if teacher is None:
        flash("Pick a teacher from the list.", "error")
        return redirect(url_for("teachers.list_teachers"))

    set_current_teacher(teacher["teacher_id"])
    flash(f"Working as {teacher['name']}.", "success")
    return redirect(url_for("units.list_units"))
