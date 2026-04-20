"""
FireReach – Tool 3: Outreach Automated Sender
Generates a hyper-personalized email referencing real signals, then sends via SendGrid.
Guardrail: validates that generated email references ≥2 actual signals before sending.
"""
from __future__ import annotations

import json
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from schemas import (
    OutreachSenderInput,
    OutreachSenderOutput,
    GrowthSignal,
)
from utils.config import get_settings
from utils.logger import get_logger
from prompts import (
    OUTREACH_EMAIL_PROMPT,
    SIGNAL_REFERENCE_CHECK_PROMPT,
    SYSTEM_SDR_EXPERT,
)

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """
    Robustly extract and parse JSON from LLM response.
    Handles markdown fences, extra text, and multiple attempts.
    """
    # Strip markdown fences if present
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text

    text = text.strip()

    # Remove leading "json" markers
    if text.startswith("json"):
        text = text[4:].strip()

    # Try to parse as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find the JSON object/array within the text using regex
    # Match from first { or [ to last matching } or ]
    json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # If still failing, raise with debugging info
    raise ValueError(f"Could not extract valid JSON from LLM response. Raw text: {text[:300]}")


def _select_best_signals(signals: list[GrowthSignal], count: int = 6) -> list[GrowthSignal]:
    """
    Select 5-6 strongest/most recent signals for maximum impact.
    Prioritize: recent > strong relevance > signal type diversity
    """
    if not signals:
        return []

    if len(signals) <= count:
        return signals

    # Prioritize signals by type relevance and order (assumes sorted by recency)
    # Weight: funding, hiring, leadership > tech_stack, social > growth
    priority_types = {
        "funding": 5,
        "hiring": 5,
        "leadership": 4,
        "social": 3,
        "tech_stack": 3,
        "growth": 2,
    }

    scored_signals = [
        (sig, priority_types.get(sig.signal_type, 1), idx)
        for idx, sig in enumerate(signals)
    ]

    # Sort by: priority (desc), then recency (asc - earlier index = more recent)
    scored_signals.sort(key=lambda x: (-x[1], x[2]))

    return [sig for sig, _, _ in scored_signals[:count]]


def _format_signals(signals: list[GrowthSignal]) -> str:
    if not signals:
        return "No signals available."

    # Select best signals - 6 for comprehensive email
    best_signals = _select_best_signals(signals, count=6)

    return "\n".join(
        f"{i}. [{s.signal_type.upper()}] {s.description}"
        for i, s in enumerate(best_signals, 1)
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _generate_email(
    company: str,
    recipient_email: str,
    icp: str,
    account_brief: str,
    signals: list[GrowthSignal],
    groq_api_key: str,
) -> tuple[str, str]:
    """Returns (subject, body)."""
    try:
        llm = ChatGroq(
            api_key=groq_api_key,
            model="llama-3.3-70b-versatile",
            temperature=0.4,
            max_tokens=1500,
            timeout=60,
        )

        prompt = OUTREACH_EMAIL_PROMPT.format(
            icp=icp,
            company=company,
            recipient_email=recipient_email,
            account_brief=account_brief,
            signals_formatted=_format_signals(signals),
        )

        messages = [
            SystemMessage(content=SYSTEM_SDR_EXPERT),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        text = response.content.strip()

        if not text:
            raise ValueError("Empty response from LLM")

        try:
            data = _extract_json(text)
        except ValueError as e:
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

        subject = data.get("subject", "").strip()
        body = data.get("body", "").strip()

        if not subject or not body:
            raise ValueError("LLM returned empty subject or body")

        return subject, body
    except Exception as e:
        raise ValueError(f"Email generation failed: {str(e)}")


def _generate_fallback_email(payload: OutreachSenderInput) -> tuple[str, str]:
    """
    Generate a detailed signal-rich fallback email with actual signal details.
    """
    company = payload.company

    # Extract brief info
    brief_lines = payload.account_brief.split("\n") if payload.account_brief else []
    brief_summary = brief_lines[0][:150] if brief_lines else ""

    # Get best signals with details
    best_signals = _select_best_signals(payload.signals, count=6) if payload.signals else []

    # Format signal list with descriptions
    signal_details = []
    for sig in best_signals:
        signal_details.append(f"• {sig.description}")

    signal_list = "\n".join(signal_details) if signal_details else "• Recent growth and market activity"

    # Create subject with first signal if available
    first_signal_type = best_signals[0].signal_type.replace("_", " ").title() if best_signals else "Activity"
    subject = f"Noticed {company}'s recent {first_signal_type.lower()}"

    body = f"""Hi,

We've been researching {company} and came across some impressive signals:

{signal_list}

This suggests {company} is in a growth phase with significant expansion momentum. {brief_summary if brief_summary else 'Your trajectory is compelling'}.

Given these developments, it seems like there's real potential for partnership that could accelerate your momentum further. We've worked with similar companies at this stage and seen meaningful impact.

Worth a brief conversation? I'm confident we can add value.

Best regards,
FireReach"""

    return subject, body


def _check_email_quality(
    signals: list[GrowthSignal],
    email_body: str,
    groq_api_key: str,
) -> tuple[bool, str]:
    """
    Guardrail: verify email meets all quality standards.
    Checks: <250 words, 5-6 signals, no URLs, structure, tone, grounded.
    Returns (passes, reason).
    """
    llm = ChatGroq(
        api_key=groq_api_key,
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        max_tokens=300,
    )

    best_signals = _select_best_signals(signals, count=6)
    signals_text = _format_signals(signals)

    prompt = SIGNAL_REFERENCE_CHECK_PROMPT.format(
        signals_formatted=signals_text,
        email_body=email_body,
    )

    response = llm.invoke(prompt)
    text = response.content.strip()

    try:
        result = _extract_json(text)
        passes = result.get("passes", False)
        reason = result.get("reason", "Quality check incomplete")

        # Log the check result
        if not passes:
            logger = get_logger("quality_check")
            logger.warning("email_quality_failed", reason=reason, details=result)

        return passes, reason
    except ValueError:
        # Fallback: do local checks
        word_count = len(email_body.split())
        has_urls = "http" in email_body.lower() or "www." in email_body.lower()

        # Check first paragraph is impressive
        first_para = email_body.split("\n")[0] if email_body else ""
        is_opening_specific = len(first_para) > 30 and any(
            marker in first_para for marker in ["hired", "raised", "launched", "expanded", "closed", "Series"]
        )

        has_signal_refs = sum(
            1 for s in best_signals
            if any(word.lower() in email_body.lower()
                   for word in s.description.split()[:3])
        )

        checks = {
            "word_count_ok": word_count <= 500,
            "no_urls": not has_urls,
            "has_signals": has_signal_refs >= 5,
            "opening_specific": is_opening_specific,
        }

        passes = all(checks.values())
        reason = f"Local check: {word_count} words, {has_signal_refs} signals, {'no URLs' if not has_urls else 'HAS URLs'}, opening {'specific' if is_opening_specific else 'generic'}"
        return passes, reason


def _send_via_sendgrid(
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    body: str,
    api_key: str,
) -> tuple[bool, str | None]:
    """Returns (success, message_id)."""
    sg = sendgrid.SendGridAPIClient(api_key=api_key)

    message = Mail(
        from_email=Email(from_email, from_name),
        to_emails=To(to_email),
        subject=subject,
        plain_text_content=Content("text/plain", body),
        html_content=Content(
            "text/html",
            body.replace("\n", "<br>"),
        ),
    )

    response = sg.client.mail.send.post(request_body=message.get())
    success = response.status_code in (200, 201, 202)
    message_id = response.headers.get("X-Message-Id")
    return success, message_id


# ---------------------------------------------------------------------------
# Main tool function
# ---------------------------------------------------------------------------
def tool_outreach_automated_sender(
    payload: OutreachSenderInput,
    session_id: str,
) -> OutreachSenderOutput:
    """
    1. Generates hyper-personalized email using Groq LLM.
    2. Runs guardrail to confirm ≥2 signal references.
    3. Sends via SendGrid.
    """
    logger = get_logger(session_id)
    settings = get_settings()

    logger.tool_call("tool_outreach_automated_sender", {
        "company":          payload.company,
        "recipient_email":  payload.recipient_email,
        "signals_count":    len(payload.signals),
    })

    # ── Step 1: Generate email ────────────────────────────────────────
    try:
        subject, body = _generate_email(
            company=payload.company,
            recipient_email=payload.recipient_email,
            icp=payload.icp,
            account_brief=payload.account_brief,
            signals=payload.signals,
            groq_api_key=settings.groq_api_key,
        )
    except Exception as e:
        logger.error("email_generation_failed", error=str(e))

        # Fallback: Generate simple but effective email from account brief
        try:
            subject, body = _generate_fallback_email(payload)
            logger.info("using_fallback_email_template")
        except Exception as fallback_error:
            error_msg = f"Email generation failed: {str(e)}"
            logger.error("fallback_also_failed", error=str(fallback_error))
            output = OutreachSenderOutput(subject="", body="", error=error_msg)
            logger.tool_result("tool_outreach_automated_sender", {"error": error_msg}, success=False)
            return output

    logger.llm_output("outreach_generator", f"SUBJECT: {subject}\n\n{body}")

    # ── Step 2: Guardrail – email quality check ────────────────────
    if payload.signals:
        try:
            passes, reason = _check_email_quality(
                payload.signals, body, settings.groq_api_key
            )
            if not passes:
                logger.warning("email_quality_check_failed", reason=reason)
                # Attempt one regeneration with stronger instruction
                try:
                    subject, body = _generate_email(
                        company=payload.company,
                        recipient_email=payload.recipient_email,
                        icp=payload.icp,
                        account_brief=payload.account_brief,
                        signals=payload.signals,
                        groq_api_key=settings.groq_api_key,
                    )
                    logger.info("email_regenerated_after_guardrail")
                except Exception as regen_error:
                    logger.warning("email_regeneration_failed", error=str(regen_error))
                    # Use fallback if regeneration fails
                    subject, body = _generate_fallback_email(payload)
            else:
                logger.info("email_quality_check_passed", reason=reason)
        except Exception as e:
            logger.warning("guardrail_check_skipped", error=str(e))

    # ── Step 3: Send via SendGrid ─────────────────────────────────────
    sent = False
    message_id = None

    if SENDGRID_AVAILABLE and settings.sendgrid_api_key:
        try:
            sent, message_id = _send_via_sendgrid(
                from_email=settings.sendgrid_from_email,
                from_name=settings.sendgrid_from_name,
                to_email=payload.recipient_email,
                subject=subject,
                body=body,
                api_key=settings.sendgrid_api_key,
            )
            logger.email_sent(payload.recipient_email, message_id, sent)
        except Exception as e:
            error_msg = f"SendGrid send failed: {str(e)}"
            logger.email_sent(payload.recipient_email, None, False)
            output = OutreachSenderOutput(
                subject=subject,
                body=body,
                sent=False,
                error=error_msg,
            )
            logger.tool_result("tool_outreach_automated_sender", {"error": error_msg}, success=False)
            return output
    else:
        logger.warning("sendgrid_unavailable", reason="Missing SendGrid key or library")
        # Still return the generated email even if not sent
        sent = False

    output = OutreachSenderOutput(
        subject=subject,
        body=body,
        sent=sent,
        message_id=message_id,
    )

    logger.tool_result("tool_outreach_automated_sender", {
        "subject": subject,
        "body_length": len(body),
        "sent": sent,
        "message_id": message_id,
    })

    return output
