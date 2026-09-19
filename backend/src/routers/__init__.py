"""
API Routers package for MedVerify.
"""
from src.routers.check import router as check_router
from src.routers.investigate import router as investigate_router
from src.routers.sessions import router as sessions_router
from src.routers.reports import router as reports_router
from src.routers.uploads import router as uploads_router
from src.routers.batches import router as batches_router
from src.routers.admin import router as admin_router

__all__ = [
    "check_router",
    "investigate_router",
    "sessions_router",
    "reports_router",
    "uploads_router",
    "batches_router",
    "admin_router",
]
