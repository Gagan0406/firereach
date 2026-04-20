"""
FireReach – API Routes
POST /run-agent        → Execute the full agent pipeline
GET  /session/{id}     → Retrieve session state
GET  /logs/{id}        → Retrieve session logs
GET  /health           → Health check
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

from schemas import RunAgentRequest, RunAgentResponse, SessionResponse
from services import get_agent_service, AgentService

router = APIRouter()


def _get_service() -> AgentService:
    return get_agent_service()


# ---------------------------------------------------------------------------
# POST /run-agent
# ---------------------------------------------------------------------------
@router.post(
    "/run-agent",
    response_model=RunAgentResponse,
    summary="Run the full FireReach agent pipeline",
    description=(
        "Accepts ICP, company, and target email. "
        "Runs Signal Harvesting → Research → Email Generation → Send."
    ),
)
async def run_agent(
    request: RunAgentRequest,
    service: AgentService = Depends(_get_service),
) -> RunAgentResponse:
    try:
        return await service.run(request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal agent error: {str(e)}")


# ---------------------------------------------------------------------------
# GET /session/{session_id}
# ---------------------------------------------------------------------------
@router.get(
    "/session/{session_id}",
    response_model=SessionResponse,
    summary="Get session state by ID",
)
async def get_session(
    session_id: str,
    service: AgentService = Depends(_get_service),
) -> SessionResponse:
    state = service.get_session(session_id)
    if state is None:
        return SessionResponse(session_id=session_id, state={}, exists=False)
    return SessionResponse(session_id=session_id, state=state, exists=True)


# ---------------------------------------------------------------------------
# GET /logs/{session_id}
# ---------------------------------------------------------------------------
@router.get(
    "/logs/{session_id}",
    summary="Get structured JSON logs for a session",
)
async def get_logs(
    session_id: str,
    service: AgentService = Depends(_get_service),
) -> JSONResponse:
    logs = service.get_logs(session_id)
    if not logs:
        raise HTTPException(
            status_code=404,
            detail=f"No logs found for session {session_id}",
        )
    return JSONResponse(content={"session_id": session_id, "logs": logs})


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------
@router.get("/health", summary="Health check")
async def health_check() -> dict:
    return {"status": "ok", "service": "FireReach"}
