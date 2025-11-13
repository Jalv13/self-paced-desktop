"""Student-specific routes for managing class enrollments."""

from typing import Union

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services import get_user_service

student_bp = Blueprint("student", __name__, url_prefix="/student")


def _require_student() -> Union[int, Response]:
    """Ensure the session belongs to a logged-in student."""
    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id:
        flash("Please log in first.", "warning")
        return redirect(url_for("auth.login"))

    if role != "student":
        flash("Student access required.", "error")
        return redirect(url_for("main.subject_selection"))

    return int(user_id)


@student_bp.route("/classes")
def view_classes():
    """Show all classes the student is enrolled in."""
    student_id_or_response = _require_student()
    if not isinstance(student_id_or_response, int):
        return student_id_or_response

    user_service = get_user_service()
    classes = user_service.get_student_classes(student_id_or_response)

    return render_template("student_classes.html", classes=classes)


@student_bp.route("/add_teacher", methods=["POST"])
def add_teacher():
    """Join a teacher's class using a class code."""
    student_id_or_response = _require_student()
    if not isinstance(student_id_or_response, int):
        return student_id_or_response

    teacher_code = request.form.get("code", "").strip().upper()
    user_service = get_user_service()
    result = user_service.add_student_via_code(student_id_or_response, teacher_code)

    if result.get("success"):
        teacher = result.get("teacher")
        teacher_name = teacher.username if teacher else "your teacher"
        flash(f"Successfully joined {teacher_name}'s class!", "success")
    else:
        flash(result.get("error") or "Unable to join class.", "error")

    return redirect(url_for("student.view_classes"))
