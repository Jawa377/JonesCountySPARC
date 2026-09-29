"""Site-level pages that don't belong to a feature blueprint: home and about."""

from flask import Blueprint, redirect, render_template, url_for

from app.functions import get_current_teacher

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    """Send the visitor to their units, or to the teacher picker if nobody is picked."""
    if get_current_teacher() is None:
        return redirect(url_for("teachers.list_teachers"))
    return redirect(url_for("units.list_units"))


@bp.get("/about")
def about():
    """Explain what SPARC Textbook Studio is and what Phase 1 covers."""
    return render_template("about.html")
