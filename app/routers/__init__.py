from app.routers.admin import router as admin_router
from app.routers.analytics import router as analytics_router
from app.routers.auth import router as auth_router
from app.routers.knowledge import router as knowledge_router
from app.routers.rag import router as rag_router
from app.routers.tickets import router as tickets_router

__all__ = [
    "admin_router",
    "analytics_router",
    "auth_router",
    "knowledge_router",
    "rag_router",
    "tickets_router",
]
