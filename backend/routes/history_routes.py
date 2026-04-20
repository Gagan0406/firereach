"""
FireReach – History Routes
GET /history                    → List all outreach history with pagination
GET /history/{session_id}       → Retrieve a specific session
GET /history/company/{company}  → Get all outreach for a company
GET /history/search?q=query     → Search history by company or ICP
DELETE /history/{session_id}    → Delete a session
GET /history/stats              → Get history statistics
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from services import get_history_service, HistoryService

router = APIRouter()


def _get_service() -> HistoryService:
    return get_history_service()


# ---------------------------------------------------------------------------
# GET /history
# ---------------------------------------------------------------------------
@router.get(
    "/history",
    summary="List all outreach sessions",
    description="Retrieve all active outreach sessions with pagination"
)
async def list_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """List all outreach sessions with pagination."""
    try:
        sessions, total = service.get_all_sessions(limit=limit, offset=offset)
        return JSONResponse(content={
            "data": sessions,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(sessions)
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


# ---------------------------------------------------------------------------
# GET /history/{session_id}
# ---------------------------------------------------------------------------
@router.get(
    "/history/{session_id}",
    summary="Get a specific session",
    description="Retrieve a single outreach session by ID"
)
async def get_history_item(
    session_id: str,
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """Retrieve a single session by ID."""
    try:
        session = service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return JSONResponse(content={"data": session})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


# ---------------------------------------------------------------------------
# GET /history/company/{company}
# ---------------------------------------------------------------------------
@router.get(
    "/history/company/{company}",
    summary="Get sessions by company",
    description="Retrieve all outreach sessions for a specific company"
)
async def get_company_history(
    company: str,
    limit: int = Query(50, ge=1, le=200),
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """Get all sessions for a specific company."""
    try:
        sessions = service.get_sessions_by_company(company, limit=limit)
        return JSONResponse(content={
            "data": sessions,
            "company": company,
            "count": len(sessions)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve company history: {str(e)}")


# ---------------------------------------------------------------------------
# GET /history/search?q=query
# ---------------------------------------------------------------------------
@router.get(
    "/history/search",
    summary="Search history",
    description="Search sessions by company name or ICP"
)
async def search_history(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(50, ge=1, le=200),
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """Search sessions by company or ICP."""
    try:
        sessions = service.search_sessions(q, limit=limit)
        return JSONResponse(content={
            "data": sessions,
            "query": q,
            "count": len(sessions)
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ---------------------------------------------------------------------------
# GET /history/stats
# ---------------------------------------------------------------------------
@router.get(
    "/history/stats",
    summary="Get history statistics",
    description="Retrieve statistics about outreach sessions"
)
async def get_stats(
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """Get statistics about all sessions."""
    try:
        stats = service.get_stats()
        return JSONResponse(content={"data": stats})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ---------------------------------------------------------------------------
# DELETE /history/{session_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/history/{session_id}",
    summary="Delete a session",
    description="Soft-delete an outreach session (marks as deleted, doesn't remove from DB)"
)
async def delete_history_item(
    session_id: str,
    hard: bool = Query(False, description="If true, permanently delete from database"),
    service: HistoryService = Depends(_get_service),
) -> JSONResponse:
    """Delete (soft or hard) a session."""
    try:
        success = service.delete_session(session_id, hard_delete=hard)
        if not success:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        return JSONResponse(content={
            "message": f"Session {'permanently deleted' if hard else 'deleted'}",
            "session_id": session_id
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


# ---------------------------------------------------------------------------
# POST /resend-email
# ---------------------------------------------------------------------------
from pydantic import BaseModel, EmailStr

class ResendEmailRequest(BaseModel):
    session_id: str
    email: EmailStr
    subject: str
    body: str

@router.post(
    "/resend-email",
    summary="Resend email from completed session",
    description="Asynchronously resend the email from a completed outreach session"
)
async def resend_email(
    request: ResendEmailRequest,
) -> JSONResponse:
    """Asynchronously resend email without blocking."""
    import asyncio
    from utils.config import get_settings

    try:
        settings = get_settings()

        # Async task to send email in background
        async def send_email_async():
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail, Email, To, Content

                sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
                message = Mail(
                    from_email=Email(settings.sendgrid_from_email, settings.sendgrid_from_name),
                    to_emails=To(request.email),
                    subject=request.subject,
                    plain_text_content=Content("text/plain", request.body),
                    html_content=Content(
                        "text/html",
                        request.body.replace("\n", "<br>"),
                    ),
                )

                response = sg.client.mail.send.post(request_body=message.get())
                success = response.status_code in (200, 201, 202)
                message_id = response.headers.get("X-Message-Id")

                return {
                    "success": success,
                    "message_id": message_id,
                    "status_code": response.status_code
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        # Fire off async task without waiting
        asyncio.create_task(send_email_async())

        return JSONResponse(content={
            "message": "Email resend queued",
            "session_id": request.session_id,
            "recipient": request.email
        }, status_code=202)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue email resend: {str(e)}")
