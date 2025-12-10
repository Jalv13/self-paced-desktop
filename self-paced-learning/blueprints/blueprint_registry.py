"""Blueprint Registration Module

Handles the registration of all application Blueprints with the Flask app.
Provides centralized Blueprint management and URL configuration.
"""

from flask import Flask
from .main_routes import main_bp
from .api_routes import api_bp
from .admin_routes import admin_bp
from .auth_routes import auth_bp
from .teacher_routes import teacher_bp
from .student_routes import student_bp


def register_blueprints(app: Flask) -> None:
    """Register all application Blueprints with the Flask app.

    Args:
        app: The Flask application instance
    """

    # Register main routes Blueprint (no URL prefix - these are core routes)
    app.register_blueprint(main_bp)

    # Register auth routes
    app.register_blueprint(auth_bp)

    # Register API routes Blueprint (with /api prefix)
    app.register_blueprint(api_bp)

    # Register teacher and student portals
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)

    # Register admin routes Blueprint (with /admin prefix)
    app.register_blueprint(admin_bp)

    print("[OK] All Blueprints registered successfully:")
    print(f"   - Auth routes: {auth_bp.name}")
    print(f"   - Main routes: {main_bp.name}")
    print(f"   - API routes: {api_bp.name} (prefix: {api_bp.url_prefix})")
    print(f"   - Teacher routes: {teacher_bp.name} (prefix: {teacher_bp.url_prefix})")
    print(f"   - Student routes: {student_bp.name} (prefix: {student_bp.url_prefix})")
    print(f"   - Admin routes: {admin_bp.name} (prefix: {admin_bp.url_prefix})")


def get_blueprint_info() -> dict:
    """Get information about all registered Blueprints.

    Returns:
        Dictionary containing Blueprint information
    """
    return {
        "main": {
            "name": main_bp.name,
            "url_prefix": main_bp.url_prefix or "/",
            "description": "Core application routes",
        },
        "api": {
            "name": api_bp.name,
            "url_prefix": api_bp.url_prefix,
            "description": "API endpoints for data and progress",
        },
        "auth": {
            "name": auth_bp.name,
            "url_prefix": auth_bp.url_prefix or "/",
            "description": "Login, registration, and logout",
        },
        "teacher": {
            "name": teacher_bp.name,
            "url_prefix": teacher_bp.url_prefix,
            "description": "Teacher dashboard routes",
        },
        "student": {
            "name": student_bp.name,
            "url_prefix": student_bp.url_prefix,
            "description": "Student class management routes",
        },
        "admin": {
            "name": admin_bp.name,
            "url_prefix": admin_bp.url_prefix,
            "description": "Administrative interface routes",
        },
    }
