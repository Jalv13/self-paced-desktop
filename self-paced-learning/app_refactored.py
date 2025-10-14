"""Compatibility shim for legacy tests expecting the refactored app entrypoint."""
from app import app  # noqa: F401

__all__ = ["app"]
