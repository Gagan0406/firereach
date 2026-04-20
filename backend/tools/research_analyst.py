"""
FireReach – Tool 2: Research Analyst
Takes harvested signals + ICP → produces Account Brief.
Guardrail: only references signals provided; no hallucination.
"""
from __future__ import annotations

import json

from tenacity import retry, stop_after_attempt, wait_exponential

from schemas import (
    ResearchAnalystInput,
    ResearchAnalystOutput,
    GrowthSignal,
)
from utils.config import get_settings
from utils.logger import get_logger
from prompts import ACCOUNT_BRIEF_PROMPT, SYSTEM_SDR_EXPERT

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


def _format_signals(signals: list[GrowthSignal]) -> str:
    if not signals:
        return "No signals available."
    lines = []
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. [{s.signal_type.upper()}] {s.description} (Source: {s.source})"
        )
    return "\n".join(lines)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _run_research_llm(
    company: str,
    icp: str,
    signals: list[GrowthSignal],
    groq_api_key: str,
) -> tuple[str, list[str], str]:
    """Returns (account_brief, pain_points, urgency_reason)."""
    llm = ChatGroq(
        api_key=groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=1000,
    )

    signals_formatted = _format_signals(signals)

    prompt = ACCOUNT_BRIEF_PROMPT.format(
        company=company,
        icp=icp,
        signals_formatted=signals_formatted,
    )

    messages = [
        SystemMessage(content=SYSTEM_SDR_EXPERT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    text = response.content.strip()

    # Parse paragraphs and bullet points from the response
    lines = text.split("\n")
    paragraphs = []
    pain_points = []
    urgency = ""
    in_bullets = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "• ", "* ")):
            in_bullets = True
            pain_points.append(line.lstrip("-•* ").strip())
        elif line.lower().startswith(("urgency", "timing", "why now")):
            urgency = line
        elif not in_bullets and len(line) > 30:
            paragraphs.append(line)

    account_brief = " ".join(paragraphs[:6])  # keep first 6 lines as brief
    if not account_brief:
        account_brief = text[:800]

    if not urgency and paragraphs:
        urgency = paragraphs[-1]

    return account_brief, pain_points[:3], urgency


def tool_research_analyst(
    payload: ResearchAnalystInput,
    session_id: str,
) -> ResearchAnalystOutput:
    """
    Generates a 2-paragraph Account Brief from harvested signals.
    Enforces that only provided signals are referenced.
    """
    logger = get_logger(session_id)
    settings = get_settings()

    logger.tool_call("tool_research_analyst", {
        "company":  payload.company,
        "icp":      payload.icp[:100],
        "signals":  len(payload.signals),
    })

    # Guardrail: require at least 1 signal to produce research
    if not payload.signals:
        msg = "No signals available for research. Cannot produce grounded account brief."
        logger.warning("research_no_signals", company=payload.company)
        output = ResearchAnalystOutput(
            account_brief=msg,
            pain_points=[],
            urgency_reason="Insufficient signal data.",
            error=msg,
        )
        logger.tool_result("tool_research_analyst", output.model_dump(), success=False)
        return output

    try:
        account_brief, pain_points, urgency_reason = _run_research_llm(
            company=payload.company,
            icp=payload.icp,
            signals=payload.signals,
            groq_api_key=settings.groq_api_key,
        )
    except Exception as e:
        error_msg = f"Research LLM failed: {str(e)}"
        logger.error("research_llm_failed", error=str(e))
        output = ResearchAnalystOutput(
            account_brief="",
            pain_points=[],
            urgency_reason="",
            error=error_msg,
        )
        logger.tool_result("tool_research_analyst", {"error": error_msg}, success=False)
        return output

    output = ResearchAnalystOutput(
        account_brief=account_brief,
        pain_points=pain_points,
        urgency_reason=urgency_reason,
    )

    logger.tool_result("tool_research_analyst", {
        "brief_length": len(account_brief),
        "pain_points": pain_points,
        "urgency": urgency_reason[:100],
    })
    logger.llm_output("research_analyst", account_brief)

    return output
