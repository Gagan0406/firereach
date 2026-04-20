"""
FireReach – Progress Emitter
Tracks and emits progress events for agent execution.
Used for real-time UI updates via streaming.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Callable, Any
from enum import Enum


class ProgressStage(str, Enum):
    """Stages of agent execution"""
    STARTED = "started"
    VALIDATING = "validating"
    HARVESTING_TAVILY = "harvesting_tavily"
    HARVESTING_APIFY = "harvesting_apify"
    HARVESTING_LINKEDIN = "harvesting_linkedin"
    HARVESTING_TWITTER = "harvesting_twitter"
    EXTRACTING_SIGNALS = "extracting_signals"
    GENERATING_EMAIL = "generating_email"
    QUALITY_CHECK = "quality_check"
    SENDING_EMAIL = "sending_email"
    COMPLETED = "completed"
    FAILED = "failed"


class ProgressEvent:
    """A single progress event"""

    def __init__(
        self,
        stage: ProgressStage,
        message: str,
        progress: int = 0,  # 0-100
        data: dict[str, Any] | None = None,
    ):
        self.stage = stage
        self.message = message
        self.progress = min(100, max(0, progress))
        self.data = data or {}
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "stage": self.stage.value,
            "message": self.message,
            "progress": self.progress,
            "data": self.data,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class ProgressTracker:
    """Tracks progress and emits events"""

    def __init__(self):
        self.events: list[ProgressEvent] = []
        self.callbacks: list[Callable[[ProgressEvent], None]] = []
        self.current_stage: ProgressStage | None = None
        self.current_progress = 0

    def on_progress(self, callback: Callable[[ProgressEvent], None]) -> None:
        """Register callback for progress events"""
        self.callbacks.append(callback)

    def emit(
        self,
        stage: ProgressStage,
        message: str,
        progress: int | None = None,
        data: dict[str, Any] | None = None,
    ) -> ProgressEvent:
        """Emit a progress event"""
        # Auto-calculate progress if not provided
        if progress is None:
            stage_order = [
                ProgressStage.STARTED,
                ProgressStage.VALIDATING,
                ProgressStage.HARVESTING_TAVILY,
                ProgressStage.HARVESTING_APIFY,
                ProgressStage.HARVESTING_LINKEDIN,
                ProgressStage.HARVESTING_TWITTER,
                ProgressStage.EXTRACTING_SIGNALS,
                ProgressStage.GENERATING_EMAIL,
                ProgressStage.QUALITY_CHECK,
                ProgressStage.SENDING_EMAIL,
                ProgressStage.COMPLETED,
            ]
            try:
                idx = stage_order.index(stage)
                progress = int((idx / len(stage_order)) * 100)
            except (ValueError, ZeroDivisionError):
                progress = self.current_progress

        self.current_stage = stage
        self.current_progress = progress

        # Create event
        event = ProgressEvent(
            stage=stage,
            message=message,
            progress=progress,
            data=data,
        )

        # Store and emit
        self.events.append(event)
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in progress callback: {e}")

        return event

    def get_events(self) -> list[dict[str, Any]]:
        """Get all events as dicts"""
        return [e.to_dict() for e in self.events]

    def clear(self) -> None:
        """Clear all events"""
        self.events.clear()
        self.current_stage = None
        self.current_progress = 0


# Global progress tracker per session
_progress_trackers: dict[str, ProgressTracker] = {}


def get_progress_tracker(session_id: str) -> ProgressTracker:
    """Get or create progress tracker for session"""
    if session_id not in _progress_trackers:
        _progress_trackers[session_id] = ProgressTracker()
    return _progress_trackers[session_id]


def clear_progress_tracker(session_id: str) -> None:
    """Clear progress tracker for session"""
    if session_id in _progress_trackers:
        del _progress_trackers[session_id]
