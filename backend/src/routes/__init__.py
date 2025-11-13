from . import dialog, health, projects  # noqa: F401 - ensure route registration
from .router import base_router as router

__all__ = ["router"]
