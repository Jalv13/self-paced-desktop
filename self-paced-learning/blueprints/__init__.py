"""Blueprints Package

Organizes Flask routes into logical Blueprint modules for better
code organization and maintainability.
"""

from .main_routes import main_bp
from .api_routes import api_bp
from .admin_routes import admin_bp
from .blueprint_registry import register_blueprints, get_blueprint_info

__all__ = ["main_bp", "api_bp", "admin_bp", "register_blueprints", "get_blueprint_info"]
