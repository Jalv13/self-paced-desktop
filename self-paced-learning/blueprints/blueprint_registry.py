"""Blueprint Registration Module

Handles the registration of all application Blueprints with the Flask app.
Provides centralized Blueprint management and URL configuration.
"""

from flask import Flask
from .main_routes import main_bp
from .api_routes import api_bp
from .admin_routes import admin_bp


def register_blueprints(app: Flask) -> None:
    """Register all application Blueprints with the Flask app.

    Args:
        app: The Flask application instance
    """

    # Register main routes Blueprint (no URL prefix - these are core routes)
    app.register_blueprint(main_bp)

    # Register API routes Blueprint (with /api prefix)
    app.register_blueprint(api_bp)

    # Register admin routes Blueprint (with /admin prefix)
    app.register_blueprint(admin_bp)

    print("[OK] All Blueprints registered successfully:")
    print(f"   - Main routes: {main_bp.name}")
    print(f"   - API routes: {api_bp.name} (prefix: {api_bp.url_prefix})")
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
        "admin": {
            "name": admin_bp.name,
            "url_prefix": admin_bp.url_prefix,
            "description": "Administrative interface routes",
        },
    }
