"""
FireReach – Agent Service
Bridges the FastAPI route layer and the LangGraph agent.
Manages session creation, graph invocation, and result persistence.
"""
from __future__ import annotations

from typing import Any

from agent import get_agent_graph
from schemas import RunAgentRequest, RunAgentResponse, AgentStatus
from services.session_store import get_session_store
from services.history_service import get_history_service
from utils.logger import get_logger
from utils.progress import get_progress_tracker, ProgressStage


class AgentService:

    def __init__(self) -> None:
        self.session_store = get_session_store()
        self.history_service = get_history_service()
        self.graph = get_agent_graph()

    async def run(self, request: RunAgentRequest) -> RunAgentResponse:
        """
        1. Creates a new session.
        2. Runs the LangGraph agent synchronously (LangGraph invoke is sync).
        3. Persists resulting state.
        4. Returns structured response.
        """
        # Create session
        session_id = self.session_store.create(
            icp=request.icp,
            company=request.company,
            email=request.email,
        )

        logger = get_logger(session_id)
        progress = get_progress_tracker(session_id)

        logger.info("agent_run_started", company=request.company, email=request.email)
        progress.emit(ProgressStage.STARTED, f"Starting outreach for {request.company}")

        # Build initial state dict for LangGraph
        initial_state: dict[str, Any] = {
            "session_id":     session_id,
            "icp":            request.icp,
            "company":        request.company,
            "email":          request.email,
            "signals":        {},
            "research_brief": "",
            "email_subject":  "",
            "email_body":     "",
            "status":         AgentStatus.INITIALIZED,
            "error":          None,
            "chat_history":   [],
        }

        # Run the graph
        try:
            progress.emit(ProgressStage.GENERATING_EMAIL, "Generating personalized email...")
            final_state = self.graph.invoke(initial_state)
            progress.emit(ProgressStage.QUALITY_CHECK, "Running quality checks...")
        except Exception as e:
            logger.error("graph_invoke_failed", error=str(e))
            progress.emit(ProgressStage.FAILED, f"Agent failed: {str(e)}")
            final_state = {
                **initial_state,
                "status": AgentStatus.FAILED,
                "error":  f"Agent graph failed: {str(e)}",
            }

        # Persist to session store (in-memory)
        self.session_store.update(session_id, final_state)

        # Persist to database (Neon)
        try:
            self.history_service.save_session(final_state)
        except Exception as e:
            logger.error("database_save_failed", error=str(e))

        logger.info("agent_run_completed", status=final_state.get("status"))

        # Emit completion
        if final_state.get("status") == AgentStatus.COMPLETE:
            progress.emit(ProgressStage.COMPLETED, "Outreach completed successfully!", data={"email_sent": True})
        else:
            progress.emit(ProgressStage.FAILED, f"Outreach failed: {final_state.get('error')}")

        return RunAgentResponse(
            session_id=session_id,
            status=str(final_state.get("status", AgentStatus.FAILED)),
            signals=final_state.get("signals", {}),
            research_brief=final_state.get("research_brief", ""),
            email_subject=final_state.get("email_subject", ""),
            email_body=final_state.get("email_body", ""),
            error=final_state.get("error"),
            chat_history=final_state.get("chat_history", []),
        )

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self.session_store.get(session_id)

    def get_logs(self, session_id: str) -> list[dict]:
        logger = get_logger(session_id)
        return logger.read_logs()


# Singleton service
_agent_service: AgentService | None = None


def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
