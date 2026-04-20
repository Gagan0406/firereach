"""
FireReach – Session Store
In-memory store for active agent sessions.
Designed to be swappable with Redis or a DB store later.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional
from threading import Lock


class SessionStore:
    """Thread-safe in-memory session store."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create(self, icp: str, company: str, email: str) -> str:
        """Create a new session; return session_id."""
        session_id = str(uuid.uuid4())
        with self._lock:
            self._store[session_id] = {
                "session_id":     session_id,
                "icp":            icp,
                "company":        company,
                "email":          email,
                "signals":        {},
                "research_brief": "",
                "email_subject":  "",
                "email_body":     "",
                "status":         "initialized",
                "error":          None,
                "chat_history":   [],
            }
        return session_id

    def get(self, session_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            return self._store.get(session_id)

    def update(self, session_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            if session_id in self._store:
                self._store[session_id].update(state)
            else:
                self._store[session_id] = state

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._store

    def all_sessions(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())


# Singleton store
_session_store = SessionStore()


def get_session_store() -> SessionStore:
    return _session_store
