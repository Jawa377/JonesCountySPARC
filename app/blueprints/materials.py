"""Materials blueprint: a unit's uploaded files (records only).

Phase 1 keeps no file contents and does no parsing: an upload records the
file's name, type (from its extension), and size, and the file itself is
discarded. Real parsing replaces size_label with slide/page counts later.
"""

import os
from pathlib import PurePath

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.db_connect import execute, query_one
from app.functions import get_owned_unit, get_unit_materials, safe_next_url, teacher_required

bp = Blueprint("materials", __name__)

ALLOWED_TYPES = {".pptx": "PPTX", ".docx": "DOCX", ".pdf": "PDF"}


def format_size(num_bytes: int) -> str:
    """Return a short human size label, e.g. "412 KB" or "3.1 MB"."""
    if num_bytes < 1024 * 1024:
        return f"{max(1, round(num_bytes / 1024))} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def measure_upload(file_storage) -> int:
    """Return an uploaded file's size in bytes without keeping its contents."""
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    stream.seek(0)
    return size


@bp.get("/unit/<int:unit_id>")
@teacher_required
def list_materials(unit_id: int):
    """List a unit's materials, with the upload form in a modal."""
    unit = get_owned_unit(unit_id)
    return render_template(
        "materials.html",
        unit=unit,
        materials=get_unit_materials(unit_id),
        allowed_types=", ".join(ALLOWED_TYPES.values()),
    )


@bp.post("/add")
@teacher_required
def add_material():
    """Record an uploaded PPTX, DOCX, or PDF against a unit."""
    unit = get_owned_unit(request.form.get("unit_id", type=int) or 0)
    back = safe_next_url(url_for("materials.list_materials", unit_id=unit["unit_id"]))

    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash("Choose a file to upload.", "error")
        return redirect(back)

    name = PurePath(upload.filename.replace("\\", "/")).name
    file_type = ALLOWED_TYPES.get(PurePath(name).suffix.lower())
    if file_type is None:
        flash(f"Only {', '.join(ALLOWED_TYPES.values())} files are supported.", "error")
        return redirect(back)

    title = PurePath(name).stem.strip()[:255] or name
    execute(
        "INSERT INTO materials (unit_id, filename, file_type, size_label) VALUES (%s, %s, %s, %s)",
        (unit["unit_id"], title, file_type, format_size(measure_upload(upload))),
    )
    flash(f"Added {title}.", "success")
    return redirect(back)


@bp.post("/delete/<int:material_id>")
@teacher_required
def delete_material(material_id: int):
    """Delete one material record the current teacher owns."""
    material = query_one("SELECT material_id, unit_id, filename FROM materials WHERE material_id = %s", (material_id,))
    if material is None:
        abort(404)
    unit = get_owned_unit(material["unit_id"])

    execute("DELETE FROM materials WHERE material_id = %s", (material_id,))
    flash(f"Removed {material['filename']}.", "success")
    return redirect(safe_next_url(url_for("materials.list_materials", unit_id=unit["unit_id"])))
