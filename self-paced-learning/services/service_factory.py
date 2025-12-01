"""Service Factory Module

Provides centralized service instantiation and dependency injection
for the learning platform application.
"""

import os
from .data_service import DataService
from .progress_service import ProgressService
from .ai_service import AIService
from .admin_service import AdminService
from .user_service import UserService


class ServiceFactory:
    """Factory class for creating and managing service instances."""

    def __init__(self, data_root_path: str):
        """Initialize the service factory with configuration."""
        self.data_root_path = data_root_path
        self._data_service = None
        self._progress_service = None
        self._ai_service = None
        self._admin_service = None
        self._user_service = None

    @property
    def data_service(self) -> DataService:
        """Get or create the data service instance."""
        if self._data_service is None:
            self._data_service = DataService(self.data_root_path)
        return self._data_service

    @property
    def progress_service(self) -> ProgressService:
        """Get or create the progress service instance."""
        if self._progress_service is None:
            self._progress_service = ProgressService()
        return self._progress_service

    @property
    def ai_service(self) -> AIService:
        """Get or create the AI service instance."""
        if self._ai_service is None:
            self._ai_service = AIService()
        return self._ai_service

    @property
    def admin_service(self) -> AdminService:
        """Get or create the admin service instance."""
        if self._admin_service is None:
            self._admin_service = AdminService(self.data_service, self.progress_service)
        return self._admin_service

    @property
    def user_service(self) -> UserService:
        """Get or create the user service instance."""
        if self._user_service is None:
            self._user_service = UserService()
        return self._user_service

    def get_all_services(self) -> dict:
        """Get all service instances as a dictionary."""
        return {
            "data_service": self.data_service,
            "progress_service": self.progress_service,
            "ai_service": self.ai_service,
            "admin_service": self.admin_service,
            "user_service": self.user_service,
        }

    def reset_services(self):
        """Reset all service instances (useful for testing)."""
        self._data_service = None
        self._progress_service = None
        self._ai_service = None
        self._admin_service = None
        self._user_service = None


# Global service factory instance (will be initialized by app)
service_factory: ServiceFactory = None


def init_services(data_root_path: str):
    """Initialize the global service factory."""
    global service_factory
    service_factory = ServiceFactory(data_root_path)


def get_service_factory() -> ServiceFactory:
    """Get the global service factory instance."""
    if service_factory is None:
        raise RuntimeError("Services not initialized. Call init_services() first.")
    return service_factory


def get_data_service() -> DataService:
    """Get the data service instance."""
    return get_service_factory().data_service


def get_progress_service() -> ProgressService:
    """Get the progress service instance."""
    return get_service_factory().progress_service


def get_ai_service() -> AIService:
    """Get the AI service instance."""
    return get_service_factory().ai_service


def get_admin_service() -> AdminService:
    """Get the admin service instance."""
    return get_service_factory().admin_service


def get_user_service() -> UserService:
    """Get the user service instance."""
    return get_service_factory().user_service
