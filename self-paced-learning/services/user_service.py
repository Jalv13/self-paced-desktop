"""User and class management service."""

import random
import string
from typing import Dict, List, Optional

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import Class, ClassRegistration, User


class UserService:
    """Encapsulates authentication and teacher/class management logic."""

    CODE_LENGTH = 6

    def _generate_class_code(self) -> str:
        """Generate a random alphanumeric class code."""
        alphabet = string.ascii_uppercase + string.digits
        return "".join(random.choices(alphabet, k=self.CODE_LENGTH))

    def _generate_unique_teacher_code(self) -> str:
        """Generate a unique teacher code."""
        while True:
            candidate = self._generate_class_code()
            if not User.query.filter_by(code=candidate).first():
                return candidate

    # --------------------------------------------------------------------- #
    # Authentication
    # --------------------------------------------------------------------- #

    def register_user(
        self, username: str, email: str, password: str, role: str
    ) -> Dict[str, object]:
        """Register a new student or teacher account."""
        role = (role or "").strip().lower()
        if role not in {"student", "teacher"}:
            return {"success": False, "error": "Role must be student or teacher."}

        if not password or len(password) < 8:
            return {"success": False, "error": "Password must be at least 8 characters."}

        if User.query.filter_by(email=email).first():
            return {"success": False, "error": "Email already registered."}

        if User.query.filter_by(username=username).first():
            return {"success": False, "error": "Username already taken."}

        try:
            password_hash = generate_password_hash(password)
            code = self._generate_unique_teacher_code() if role == "teacher" else None

            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                code=code,
            )
            db.session.add(user)
            db.session.commit()

            return {"success": True, "user": user}
        except Exception as exc:
            current_app.logger.exception("Failed to register user: %s", exc)
            db.session.rollback()
            return {"success": False, "error": "Registration failed. Try again."}

    def authenticate(self, identifier: str, password: str) -> Optional[User]:
        """
        Validate credentials (email or username) and return the user if valid.

        A default admin account (username/email: admin / admin@example.com, password: admin123)
        is created on-the-fly if it does not already exist when matching credentials are provided.
        """
        identifier = (identifier or "").strip()
        lookup_email = None
        lookup_username = None

        if "@" in identifier:
            lookup_email = identifier
        else:
            lookup_username = identifier

        user = None
        if lookup_email:
            user = User.query.filter_by(email=lookup_email).first()
        if not user and lookup_username:
            user = User.query.filter_by(username=lookup_username).first()

        # Auto-provision a default admin account when the known credentials are provided.
        admin_username = "admin"
        admin_email = "admin@example.com"
        admin_password = "admin123"

        if not user and identifier.lower() in {admin_username, admin_email} and password == admin_password:
            try:
                password_hash = generate_password_hash(admin_password)
                user = User(
                    username=admin_username,
                    email=admin_email,
                    password_hash=password_hash,
                    role="teacher",  # reuse teacher role; admin access is session-gated
                    code=None,
                )
                db.session.add(user)
                db.session.commit()
            except Exception as exc:
                if current_app:
                    current_app.logger.exception("Failed to create default admin: %s", exc)
                db.session.rollback()
                user = None

        if user and check_password_hash(user.password_hash, password):
            return user
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Return a user by id."""
        return User.query.get(user_id)

    # --------------------------------------------------------------------- #
    # Teacher / Student Relationships
    # --------------------------------------------------------------------- #

    def get_teacher_students(self, teacher_id: int) -> List[User]:
        """Return a list of distinct students enrolled in the teacher's classes."""
        return (
            User.query.join(
                ClassRegistration, ClassRegistration.student_id == User.id
            )
            .join(Class, Class.id == ClassRegistration.class_id)
            .filter(Class.teacher_id == teacher_id, User.role == "student")
            .distinct()
            .order_by(User.username.asc())
            .all()
        )

    def remove_student_from_teacher(self, teacher_id: int, student_id: int) -> None:
        """Remove a student's registration from all of the teacher's classes."""
        registrations = (
            ClassRegistration.query.join(Class, Class.id == ClassRegistration.class_id)
            .filter(
                Class.teacher_id == teacher_id,
                ClassRegistration.student_id == student_id,
            )
            .all()
        )

        if not registrations:
            return

        try:
            for registration in registrations:
                db.session.delete(registration)
            db.session.commit()
        except Exception as exc:
            current_app.logger.exception("Failed to remove student: %s", exc)
            db.session.rollback()

    def add_student_via_code(
        self, student_id: int, teacher_code: str
    ) -> Dict[str, object]:
        """Register a student into all classes owned by a teacher code."""
        teacher_code = (teacher_code or "").strip().upper()
        if not teacher_code:
            return {"success": False, "error": "Teacher code is required."}

        teacher = User.query.filter_by(code=teacher_code, role="teacher").first()
        if not teacher:
            return {"success": False, "error": "Invalid teacher code."}

        classes = Class.query.filter_by(teacher_id=teacher.id).all()

        # Ensure teacher has at least one class to attach registrations to.
        if not classes:
            default_class = Class(
                name=f"{teacher.username}'s Class",
                code=teacher.code,
                teacher_id=teacher.id,
            )
            db.session.add(default_class)
            db.session.commit()
            classes = [default_class]

        created = 0
        try:
            for class_ in classes:
                existing = ClassRegistration.query.filter_by(
                    student_id=student_id, class_id=class_.id
                ).first()
                if existing:
                    continue
                db.session.add(
                    ClassRegistration(student_id=student_id, class_id=class_.id)
                )
                created += 1

            db.session.commit()
            message = (
                f"Joined {teacher.username}'s classes."
                if created
                else "You are already enrolled in this teacher's classes."
            )
            return {"success": True, "message": message, "teacher": teacher}
        except Exception as exc:
            current_app.logger.exception("Failed to join teacher classes: %s", exc)
            db.session.rollback()
            return {"success": False, "error": "Unable to join teacher classes."}

    def get_student_classes(self, student_id: int) -> List[Dict[str, str]]:
        """Return all classes the student is registered in with teacher info."""
        results = (
            db.session.query(Class, User.username.label("teacher_username"))
            .join(User, Class.teacher_id == User.id)
            .join(ClassRegistration, ClassRegistration.class_id == Class.id)
            .filter(ClassRegistration.student_id == student_id)
            .all()
        )

        return [
            {"class_name": class_.name, "teacher_username": teacher_username}
            for class_, teacher_username in results
        ]
