"""
FireReach – LangGraph Agent Workflow
Flow: Input Validation → Signal Harvesting → Research Analysis → Email Generation → Send

Uses TypedDict-compatible state passed through LangGraph nodes.
Each node updates a subset of AgentState fields.
"""
from __future__ import annotations

import copy
from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from schemas import (
    AgentState,
    AgentStatus,
    SignalHarvesterInput,
    ResearchAnalystInput,
    OutreachSenderInput,
    GrowthSignal,
)
from tools import (
    tool_signal_harvester,
    tool_research_analyst,
    tool_outreach_automated_sender,
)
from utils.logger import get_logger


# ---------------------------------------------------------------------------
# Type alias for graph state dict (LangGraph works with plain dicts)
# ---------------------------------------------------------------------------
StateDict = dict[str, Any]


# ---------------------------------------------------------------------------
# Helper: update state dict and append to chat history
# ---------------------------------------------------------------------------
def _update(state: StateDict, updates: dict[str, Any]) -> StateDict:
    state = copy.deepcopy(state)
    state.update(updates)
    return state


def _append_chat(state: StateDict, role: str, content: str) -> StateDict:
    history = state.get("chat_history", [])
    history = history + [{"role": role, "content": content}]
    return _update(state, {"chat_history": history})


# ---------------------------------------------------------------------------
# Node 1: Input Validation
# ---------------------------------------------------------------------------
def node_input_validation(state: StateDict) -> StateDict:
    session_id = state.get("session_id", "unknown")
    logger = get_logger(session_id)
    logger.info("node_started", node="input_validation")

    errors: list[str] = []

    email = state.get("email", "").strip()
    company = state.get("company", "").strip()
    icp = state.get("icp", "").strip()

    if not email or "@" not in email:
        errors.append("Invalid or missing email address")
        logger.validation_failure("email", "Missing or malformed")

    if not company:
        errors.append("Company name is required")
        logger.validation_failure("company", "Empty value")

    if not icp or len(icp) < 10:
        errors.append("ICP must be at least 10 characters")
        logger.validation_failure("icp", "Too short or empty")

    if errors:
        error_msg = "; ".join(errors)
        state = _append_chat(state, "system", f"❌ Validation failed: {error_msg}")
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  error_msg,
        })

    state = _append_chat(state, "system", f"✅ Inputs validated. Starting outreach for **{company}**.")
    logger.info("node_completed", node="input_validation")
    return _update(state, {"status": AgentStatus.HARVESTING})


# ---------------------------------------------------------------------------
# Node 2: Signal Harvesting
# ---------------------------------------------------------------------------
def node_signal_harvesting(state: StateDict) -> StateDict:
    session_id = state.get("session_id", "unknown")
    logger = get_logger(session_id)
    logger.info("node_started", node="signal_harvesting")

    state = _append_chat(state, "system", f"🔍 Harvesting live signals for **{state['company']}**...")

    try:
        result = tool_signal_harvester(
            payload=SignalHarvesterInput(
                company=state["company"],
                icp=state["icp"],
            ),
            session_id=session_id,
        )
    except Exception as e:
        logger.error("signal_harvesting_node_failed", error=str(e))
        state = _append_chat(state, "system", f"⚠️ Signal harvesting encountered an error: {str(e)}")
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  f"Signal harvesting failed: {str(e)}",
        })

    if result.error and not result.signals:
        state = _append_chat(state, "system", f"⚠️ No signals found: {result.error}")
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  result.error,
        })

    # Serialize signals to dict list for state storage
    signals_dict = {
        "signals": [s.model_dump() for s in result.signals],
        "raw_snippets": result.raw_snippets,
    }

    signal_summary = f"📡 Found **{len(result.signals)} signals**: " + ", ".join(
        f"{s.signal_type}" for s in result.signals[:5]
    )
    state = _append_chat(state, "assistant", signal_summary)

    logger.info("node_completed", node="signal_harvesting", signals=len(result.signals))
    return _update(state, {
        "signals": signals_dict,
        "status":  AgentStatus.RESEARCHING,
    })


# ---------------------------------------------------------------------------
# Node 3: Research Analysis
# ---------------------------------------------------------------------------
def node_research_analysis(state: StateDict) -> StateDict:
    session_id = state.get("session_id", "unknown")
    logger = get_logger(session_id)
    logger.info("node_started", node="research_analysis")

    state = _append_chat(state, "system", "🧠 Analyzing account and building research brief...")

    signals_raw = state.get("signals", {}).get("signals", [])
    signals = [GrowthSignal(**s) for s in signals_raw]

    try:
        result = tool_research_analyst(
            payload=ResearchAnalystInput(
                company=state["company"],
                icp=state["icp"],
                signals=signals,
            ),
            session_id=session_id,
        )
    except Exception as e:
        logger.error("research_node_failed", error=str(e))
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  f"Research analysis failed: {str(e)}",
        })

    if result.error:
        state = _append_chat(state, "system", f"⚠️ Research issue: {result.error}")
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  result.error,
        })

    brief_preview = result.account_brief[:200] + ("..." if len(result.account_brief) > 200 else "")
    state = _append_chat(state, "assistant", f"📋 Account Brief ready: {brief_preview}")

    logger.info("node_completed", node="research_analysis")
    return _update(state, {
        "research_brief": result.account_brief,
        "status":         AgentStatus.GENERATING,
    })


# ---------------------------------------------------------------------------
# Node 4: Email Generation + Sending
# ---------------------------------------------------------------------------
def node_email_generation_and_send(state: StateDict) -> StateDict:
    session_id = state.get("session_id", "unknown")
    logger = get_logger(session_id)
    logger.info("node_started", node="email_generation_and_send")

    state = _append_chat(state, "system", "✉️ Generating hyper-personalized outreach email...")

    signals_raw = state.get("signals", {}).get("signals", [])
    signals = [GrowthSignal(**s) for s in signals_raw]

    try:
        result = tool_outreach_automated_sender(
            payload=OutreachSenderInput(
                company=state["company"],
                recipient_email=state["email"],
                icp=state["icp"],
                account_brief=state.get("research_brief", ""),
                signals=signals,
            ),
            session_id=session_id,
        )
    except Exception as e:
        logger.error("email_send_node_failed", error=str(e))
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  f"Email generation/send failed: {str(e)}",
        })

    if result.error and not result.body:
        return _update(state, {
            "status": AgentStatus.FAILED,
            "error":  result.error,
        })

    status_msg = (
        f"🚀 Email sent to **{state['email']}**!" if result.sent
        else f"📝 Email generated (not sent – check SendGrid config). Subject: **{result.subject}**"
    )
    state = _append_chat(state, "assistant", status_msg)

    logger.info("node_completed", node="email_generation_and_send", sent=result.sent)
    return _update(state, {
        "email_subject": result.subject,
        "email_body":    result.body,
        "status":        AgentStatus.COMPLETE,
        "error":         result.error,  # may be a soft warning
    })


# ---------------------------------------------------------------------------
# Conditional edge router
# ---------------------------------------------------------------------------
def should_continue(state: StateDict) -> str:
    """Routes to next node or END based on current status."""
    status = state.get("status", AgentStatus.FAILED)
    if status == AgentStatus.FAILED:
        return "end"
    return "continue"


# ---------------------------------------------------------------------------
# Build the compiled graph
# ---------------------------------------------------------------------------
def build_agent_graph() -> CompiledStateGraph:
    """Constructs and compiles the FireReach LangGraph workflow."""
    workflow = StateGraph(StateDict)

    # Add nodes
    workflow.add_node("input_validation",         node_input_validation)
    workflow.add_node("signal_harvesting",         node_signal_harvesting)
    workflow.add_node("research_analysis",         node_research_analysis)
    workflow.add_node("email_generation_and_send", node_email_generation_and_send)

    # Entry point
    workflow.set_entry_point("input_validation")

    # Conditional edges after each node
    for node in ["input_validation", "signal_harvesting", "research_analysis"]:
        next_map = {
            "input_validation":  "signal_harvesting",
            "signal_harvesting": "research_analysis",
            "research_analysis": "email_generation_and_send",
        }
        workflow.add_conditional_edges(
            node,
            should_continue,
            {
                "continue": next_map[node],
                "end":      END,
            },
        )

    # Final node goes to END
    workflow.add_edge("email_generation_and_send", END)

    return workflow.compile()


# Module-level compiled graph (singleton)
_compiled_graph: CompiledStateGraph | None = None


def get_agent_graph() -> CompiledStateGraph:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
    return _compiled_graph
