"""
FireReach – Database ORM Models
SQLAlchemy models for persistent storage.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index, Boolean, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class SessionDB(Base):
    """
    Persistent session storage model.
    Maps directly to the 'sessions' table in PostgreSQL.
    """
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), unique=True, nullable=False, index=True)

    # Input parameters
    icp = Column(Text, nullable=False)
    company = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=False)

    # Execution results
    signals = Column(JSON, default=dict, nullable=False)              # Serialized signals dict
    research_brief = Column(Text, default="", nullable=False)
    email_subject = Column(String(255), default="", nullable=False)
    email_body = Column(Text, default="", nullable=False)

    # Status tracking
    status = Column(String(50), default="initialized", nullable=False, index=True)
    error = Column(Text, nullable=True)
    chat_history = Column(JSON, default=list, nullable=False)         # Serialized list of messages

    # Audit timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True, index=True)          # Soft delete timestamp

    __table_args__ = (
        Index('ix_session_id', 'session_id'),
        Index('ix_company', 'company'),
        Index('ix_status', 'status'),
        Index('ix_created_at', 'created_at'),
        Index('ix_deleted_at', 'deleted_at'),
    )

    def to_dict(self) -> dict:
        """Convert ORM model to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "icp": self.icp,
            "company": self.company,
            "email": self.email,
            "signals": self.signals or {},
            "research_brief": self.research_brief,
            "email_subject": self.email_subject,
            "email_body": self.email_body,
            "status": self.status,
            "error": self.error,
            "chat_history": self.chat_history or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<SessionDB(id={self.id}, session_id={self.session_id}, company={self.company}, status={self.status})>"
