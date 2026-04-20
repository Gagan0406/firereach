"""
FireReach – History Service
CRUD operations for persistent outreach history in Neon database.
"""
from __future__ import annotations

from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime

from services.database import SessionLocal
from services.database_models import SessionDB
from utils.logger import get_logger


class HistoryService:
    """Database-backed CRUD service for outreach sessions."""

    def __init__(self) -> None:
        self.logger = get_logger("HistoryService")

    def _get_db(self) -> Session:
        """Get database session."""
        return SessionLocal()

    def save_session(self, state: dict[str, Any]) -> SessionDB:
        """Save or update a session to the database."""
        db = self._get_db()
        try:
            session_id = state.get("session_id")

            # Check if session exists
            existing = db.query(SessionDB).filter(SessionDB.session_id == session_id).first()

            if existing:
                # Update existing session
                existing.icp = state.get("icp", existing.icp)
                existing.company = state.get("company", existing.company)
                existing.email = state.get("email", existing.email)
                existing.signals = state.get("signals", {})
                existing.research_brief = state.get("research_brief", "")
                existing.email_subject = state.get("email_subject", "")
                existing.email_body = state.get("email_body", "")
                existing.status = str(state.get("status", "unknown"))
                existing.error = state.get("error")
                existing.chat_history = state.get("chat_history", [])
                existing.updated_at = datetime.utcnow()
                db.commit()
                self.logger.info(f"session_updated", session_id=session_id)
                return existing
            else:
                # Create new session
                new_session = SessionDB(
                    session_id=session_id,
                    icp=state.get("icp", ""),
                    company=state.get("company", ""),
                    email=state.get("email", ""),
                    signals=state.get("signals", {}),
                    research_brief=state.get("research_brief", ""),
                    email_subject=state.get("email_subject", ""),
                    email_body=state.get("email_body", ""),
                    status=str(state.get("status", "initialized")),
                    error=state.get("error"),
                    chat_history=state.get("chat_history", []),
                )
                db.add(new_session)
                db.commit()
                db.refresh(new_session)
                self.logger.info(f"session_created", session_id=session_id)
                return new_session
        except Exception as e:
            db.rollback()
            self.logger.error(f"save_session_failed", error=str(e))
            raise
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a single session by ID."""
        db = self._get_db()
        try:
            session = db.query(SessionDB).filter(
                SessionDB.session_id == session_id,
                SessionDB.deleted_at.is_(None)
            ).first()

            if session:
                return session.to_dict()
            return None
        finally:
            db.close()

    def get_all_sessions(self, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        """Retrieve all active sessions with pagination."""
        db = self._get_db()
        try:
            # Get total count
            total = db.query(func.count(SessionDB.id)).filter(
                SessionDB.deleted_at.is_(None)
            ).scalar()

            # Get paginated results, ordered by most recent first
            sessions = db.query(SessionDB).filter(
                SessionDB.deleted_at.is_(None)
            ).order_by(desc(SessionDB.created_at)).offset(offset).limit(limit).all()

            return [s.to_dict() for s in sessions], total
        finally:
            db.close()

    def get_sessions_by_company(self, company: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all sessions for a specific company."""
        db = self._get_db()
        try:
            sessions = db.query(SessionDB).filter(
                SessionDB.company.ilike(f"%{company}%"),
                SessionDB.deleted_at.is_(None)
            ).order_by(desc(SessionDB.created_at)).limit(limit).all()

            return [s.to_dict() for s in sessions]
        finally:
            db.close()

    def delete_session(self, session_id: str, hard_delete: bool = False) -> bool:
        """Soft delete (mark deleted_at) or hard delete a session."""
        db = self._get_db()
        try:
            session = db.query(SessionDB).filter(SessionDB.session_id == session_id).first()

            if not session:
                return False

            if hard_delete:
                db.delete(session)
            else:
                session.deleted_at = datetime.utcnow()

            db.commit()
            self.logger.info(f"session_deleted", session_id=session_id, hard=hard_delete)
            return True
        except Exception as e:
            db.rollback()
            self.logger.error(f"delete_session_failed", error=str(e))
            raise
        finally:
            db.close()

    def search_sessions(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search sessions by company or ICP."""
        db = self._get_db()
        try:
            sessions = db.query(SessionDB).filter(
                (SessionDB.company.ilike(f"%{query}%")) |
                (SessionDB.icp.ilike(f"%{query}%")),
                SessionDB.deleted_at.is_(None)
            ).order_by(desc(SessionDB.created_at)).limit(limit).all()

            return [s.to_dict() for s in sessions]
        finally:
            db.close()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about sessions."""
        db = self._get_db()
        try:
            total = db.query(func.count(SessionDB.id)).filter(
                SessionDB.deleted_at.is_(None)
            ).scalar()

            completed = db.query(func.count(SessionDB.id)).filter(
                SessionDB.status == "complete",
                SessionDB.deleted_at.is_(None)
            ).scalar()

            failed = db.query(func.count(SessionDB.id)).filter(
                SessionDB.status == "failed",
                SessionDB.deleted_at.is_(None)
            ).scalar()

            return {
                "total_sessions": total,
                "completed": completed,
                "failed": failed,
                "success_rate": round((completed / total * 100) if total > 0 else 0, 2)
            }
        finally:
            db.close()


# Singleton service
_history_service: HistoryService | None = None


def get_history_service() -> HistoryService:
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
