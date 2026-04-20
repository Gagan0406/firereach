from fastapi import APIRouter
from .agent_routes import router as agent_router
from .history_routes import router as history_router
from .streaming_routes import router as streaming_router

router = APIRouter()
router.include_router(agent_router, tags=["Agent"])
router.include_router(history_router, tags=["History"])
router.include_router(streaming_router, tags=["Streaming"])

__all__ = ["router"]
