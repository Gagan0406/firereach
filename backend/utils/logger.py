"""
FireReach – Structured Logging
One JSON log file per session. Logs all tool calls, LLM outputs, and errors.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from utils.config import get_settings

_loggers: dict[str, "SessionLogger"] = {}


class SessionLogger:
    """
    Writes structured JSON log lines to:
      {log_dir}/{session_id}.jsonl
    Also echoes WARNING+ to stdout.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        settings = get_settings()
        log_dir = Path(settings.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        self._path = log_dir / f"{session_id}.jsonl"
        self._file = self._path.open("a", encoding="utf-8")

    # ------------------------------------------------------------------
    def _write(self, level: str, event: str, **data: Any) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     level,
            "session_id": self.session_id,
            "event":     event,
            **data,
        }
        line = json.dumps(entry, default=str)
        self._file.write(line + "\n")
        self._file.flush()

        if level in ("WARNING", "ERROR", "CRITICAL"):
            print(f"[{level}] {event} | {data}", file=sys.stderr)

    # Public API -------------------------------------------------------
    def info(self, event: str, **data: Any) -> None:
        self._write("INFO", event, **data)

    def warning(self, event: str, **data: Any) -> None:
        self._write("WARNING", event, **data)

    def error(self, event: str, **data: Any) -> None:
        self._write("ERROR", event, **data)

    def tool_call(self, tool_name: str, inputs: Any) -> None:
        self._write("INFO", "tool_call", tool=tool_name, inputs=inputs)

    def tool_result(self, tool_name: str, outputs: Any, success: bool = True) -> None:
        level = "INFO" if success else "ERROR"
        self._write(level, "tool_result", tool=tool_name, outputs=outputs, success=success)

    def llm_output(self, node: str, output: str) -> None:
        self._write("INFO", "llm_output", node=node, output=output[:2000])

    def validation_failure(self, field: str, reason: str) -> None:
        self._write("WARNING", "validation_failure", field=field, reason=reason)

    def email_sent(self, recipient: str, message_id: Optional[str], success: bool) -> None:
        level = "INFO" if success else "ERROR"
        self._write(level, "email_sent", recipient=recipient, message_id=message_id, success=success)

    def close(self) -> None:
        self._file.close()

    def read_logs(self) -> list[dict]:
        """Return all log entries for this session as a list of dicts."""
        self._file.flush()
        entries = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries


def get_logger(session_id: str) -> SessionLogger:
    if session_id not in _loggers:
        _loggers[session_id] = SessionLogger(session_id)
    return _loggers[session_id]
