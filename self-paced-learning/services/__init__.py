"""Services Package

Service layer for the learning platform application.
Provides organized business logic separated from Flask routes.
"""

from .data_service import DataService
from .progress_service import ProgressService
from .ai_service import AIService
from .admin_service import AdminService
from .user_service import UserService
from .service_factory import (
    ServiceFactory,
    init_services,
    get_service_factory,
    get_data_service,
    get_progress_service,
    get_ai_service,
    get_admin_service,
    get_user_service,
)

__all__ = [
    "DataService",
    "ProgressService",
    "AIService",
    "AdminService",
    "UserService",
    "ServiceFactory",
    "init_services",
    "get_service_factory",
    "get_data_service",
    "get_progress_service",
    "get_ai_service",
    "get_admin_service",
    "get_user_service",
]
