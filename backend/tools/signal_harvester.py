"""
FireReach – Tool 1: Signal Harvester
Gathers live company signals via Tavily (web search) and Apify Google Search.
Returns only grounded signals traceable to tool output.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schemas import (
    SignalHarvesterInput,
    SignalHarvesterOutput,
    GrowthSignal,
)
from utils.config import get_settings
from utils.logger import get_logger
from utils.progress import get_progress_tracker, ProgressStage
from prompts import SIGNAL_INTERPRETER_PROMPT

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None  # type: ignore

try:
    from apify_client import ApifyClient
except ImportError:
    ApifyClient = None  # type: ignore

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None  # type: ignore


# ---------------------------------------------------------------------------
# Search queries
# ---------------------------------------------------------------------------
_YEAR = datetime.now().year

SIGNAL_QUERIES = [
    "{company} funding round " + str(_YEAR - 1) + " " + str(_YEAR),
    "{company} hiring engineers expansion",
    "{company} new CTO CEO leadership change",
    "{company} technology stack migration cloud",
    "{company} growth revenue customers announcement",
    "{company} series A B C investment news",
]


def _build_queries(company: str) -> list[str]:
    return [q.format(company=company) for q in SIGNAL_QUERIES]


def _extract_json(text: str) -> dict | list:
    """Robustly extract JSON from LLM response."""
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text

    text = text.strip()

    if text.startswith("json"):
        text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON. Raw: {text[:200]}")


# ---------------------------------------------------------------------------
# Tavily search
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _tavily_search(query: str, api_key: str) -> list[dict[str, Any]]:
    """Returns list of {title, url, content} dicts."""
    client = TavilyClient(api_key=api_key)
    result = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_answer=False,
        include_raw_content=False,
    )
    return result.get("results", [])


# ---------------------------------------------------------------------------
# Apify – Google Search scraper
# ---------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _apify_search(company: str, apify_token: str) -> list[str]:
    """
    Uses Apify's Google Search Scraper to fetch recent news snippets.
    Returns list of plain-text snippets.
    """
    client = ApifyClient(apify_token)
    run = client.actor("apify/google-search-scraper").call(
        run_input={
            "queries": f"{company} funding OR hiring OR leadership OR growth {_YEAR - 1} {_YEAR}",
            "resultsPerPage": 10,
            "maxPagesPerQuery": 1,
            "languageCode": "en",
        }
    )
    snippets: list[str] = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        for organic in item.get("organicResults", []):
            snippet = organic.get("snippet", "")
            url     = organic.get("url", "")
            if snippet:
                snippets.append(f"{snippet} [Source: {url}]")
    return snippets


# ---------------------------------------------------------------------------
# LLM-based signal extractor (uses Groq)
# ---------------------------------------------------------------------------
def _extract_signals_with_llm(
    company: str,
    raw_snippets: list[str],
    groq_api_key: str,
) -> list[GrowthSignal]:
    """
    Passes raw snippets to an LLM that extracts only grounded signals.
    """
    if not raw_snippets:
        return []

    llm = ChatGroq(
        api_key=groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        max_tokens=1500,
    )

    prompt = SIGNAL_INTERPRETER_PROMPT.format(
        company=company,
        raw_snippets="\n\n---\n\n".join(raw_snippets[:20]),
    )

    response = llm.invoke(prompt)
    text = response.content.strip()

    try:
        data = _extract_json(text)
        signals = []
        for item in data:
            try:
                signals.append(GrowthSignal(**item))
            except Exception:
                pass
        return signals
    except (ValueError, json.JSONDecodeError):
        return []


# ---------------------------------------------------------------------------
# Main tool function
# ---------------------------------------------------------------------------
def tool_signal_harvester(
    payload: SignalHarvesterInput,
    session_id: str,
) -> SignalHarvesterOutput:
    """
    Orchestrates Tavily + Apify Google Search signal gathering for a target company.
    """
    logger = get_logger(session_id)
    settings = get_settings()

    logger.tool_call("tool_signal_harvester", payload.model_dump())
    progress = get_progress_tracker(session_id)

    all_snippets: list[str] = []
    errors: list[str] = []

    # ── Tavily search ──────────────────────────────────────────────────
    progress.emit(ProgressStage.HARVESTING_TAVILY, f"Searching Tavily for {payload.company} signals...")
    if TavilyClient and settings.tavily_api_key:
        queries = _build_queries(payload.company)
        tavily_count = 0
        for query in queries[:4]:
            try:
                results = _tavily_search(query, settings.tavily_api_key)
                print(f"[Tavily] Query: '{query}' -> {len(results)} results")
                for r in results:
                    print(f"  - {r.get('title', '')[:80]}")
                    snippet = f"{r.get('title', '')} — {r.get('content', '')} [Source: {r.get('url', 'Tavily')}]"
                    all_snippets.append(snippet)
                    tavily_count += 1
            except Exception as e:
                errors.append(f"Tavily query '{query}' failed: {str(e)}")
                logger.error("tavily_query_failed", query=query, error=str(e))
        print(f"[Tavily] Total snippets collected: {tavily_count}")
        progress.emit(ProgressStage.HARVESTING_TAVILY, f"Tavily: Found {tavily_count} snippets")
    else:
        errors.append("Tavily unavailable (missing key or library)")
        logger.warning("tavily_skipped", reason="missing key or library")

    # ── Apify Google Search ───────────────────────────────────────────
    progress.emit(ProgressStage.HARVESTING_APIFY, "Searching Google via Apify...")
    if ApifyClient and settings.apify_token:
        try:
            apify_snippets = _apify_search(payload.company, settings.apify_token)
            print(f"[Apify Google] Snippets collected: {len(apify_snippets)}")
            for s in apify_snippets[:5]:
                print(f"  - {s[:80]}")
            all_snippets.extend(apify_snippets)
            progress.emit(ProgressStage.HARVESTING_APIFY, f"Apify Google: Found {len(apify_snippets)} results")
        except Exception as e:
            errors.append(f"Apify Google Search failed: {str(e)}")
            logger.error("apify_search_failed", error=str(e))
            progress.emit(ProgressStage.HARVESTING_APIFY, "Apify Google: Failed, continuing...")
    else:
        errors.append("Apify unavailable (missing key or library)")
        logger.warning("apify_skipped", reason="missing key or library")

    # Deduplicate snippets
    seen: set[str] = set()
    unique_snippets: list[str] = []
    for s in all_snippets:
        key = s[:100]
        if key not in seen:
            seen.add(key)
            unique_snippets.append(s)

    # ── LLM signal extraction ─────────────────────────────────────────
    progress.emit(ProgressStage.EXTRACTING_SIGNALS, f"Extracting signals from {len(unique_snippets)} snippets...")
    signals: list[GrowthSignal] = []
    if unique_snippets and settings.groq_api_key:
        try:
            signals = _extract_signals_with_llm(
                payload.company,
                unique_snippets,
                settings.groq_api_key,
            )
            print(f"[LLM Signal Extraction] {len(unique_snippets)} snippets -> {len(signals)} signals extracted")
            for s in signals:
                print(f"  [{s.signal_type.upper()}] {s.description[:100]}")
            progress.emit(ProgressStage.EXTRACTING_SIGNALS, f"Extracted {len(signals)} signals", data={"signals_count": len(signals)})
        except Exception as e:
            errors.append(f"Signal extraction LLM failed: {str(e)}")
            logger.error("signal_extraction_failed", error=str(e))

    output = SignalHarvesterOutput(
        company=payload.company,
        signals=signals,
        raw_snippets=unique_snippets[:10],
        error="; ".join(errors) if errors and not signals else None,
    )

    logger.tool_result(
        "tool_signal_harvester",
        {
            "signals_found": len(signals),
            "snippets_collected": len(unique_snippets),
            "errors": errors,
        },
        success=len(signals) > 0 or len(unique_snippets) > 0,
    )

    return output
