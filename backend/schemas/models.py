"""
FireReach – Pydantic Schemas
All typed models for requests, responses, state, and tool I/O.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from enum import Enum
import uuid


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AgentStatus(str, Enum):
    INITIALIZED   = "initialized"
    VALIDATING    = "validating"
    HARVESTING    = "harvesting"
    RESEARCHING   = "researching"
    GENERATING    = "generating"
    SENDING       = "sending"
    COMPLETE      = "complete"
    FAILED        = "failed"


# ---------------------------------------------------------------------------
# Core Agent State  (LangGraph TypedDict-compatible via Pydantic)
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    session_id:     str = Field(default_factory=lambda: str(uuid.uuid4()))
    icp:            str = Field(..., min_length=10, description="Ideal Customer Profile")
    company:        str = Field(..., min_length=2, description="Target company name")
    email:          str = Field(..., description="Target recipient email")

    signals:        dict[str, Any] = Field(default_factory=dict)
    research_brief: str = ""
    email_subject:  str = ""
    email_body:     str = ""

    status:         AgentStatus = AgentStatus.INITIALIZED
    error:          Optional[str] = None
    chat_history:   list[dict[str, str]] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Company name cannot be empty")
        return v

    @field_validator("icp")
    @classmethod
    def validate_icp(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("ICP must be at least 10 characters")
        return v

    class Config:
        use_enum_values = True


# ---------------------------------------------------------------------------
# Tool I/O schemas
# ---------------------------------------------------------------------------

class SignalHarvesterInput(BaseModel):
    company: str
    icp:     str

class GrowthSignal(BaseModel):
    signal_type:  str   = Field(..., description="e.g. funding, hiring, leadership, tech_stack, social")
    description:  str
    source:       str   = Field(..., description="URL or tool that produced this signal")
    grounded:     bool  = Field(True, description="True = came directly from tool output")

class SignalHarvesterOutput(BaseModel):
    company:        str
    signals:        list[GrowthSignal] = Field(default_factory=list)
    raw_snippets:   list[str]          = Field(default_factory=list, description="Raw text returned by search tools")
    error:          Optional[str]      = None


class ResearchAnalystInput(BaseModel):
    company:  str
    icp:      str
    signals:  list[GrowthSignal]

class ResearchAnalystOutput(BaseModel):
    account_brief: str  = Field(..., min_length=50, description="2-paragraph account brief")
    pain_points:   list[str]
    urgency_reason: str
    error:         Optional[str] = None


class OutreachSenderInput(BaseModel):
    company:        str
    recipient_email: str
    icp:            str
    account_brief:  str
    signals:        list[GrowthSignal]

class OutreachSenderOutput(BaseModel):
    subject:    str
    body:       str
    sent:       bool   = False
    message_id: Optional[str] = None
    error:      Optional[str] = None


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------

class RunAgentRequest(BaseModel):
    icp:     str = Field(..., min_length=10)
    company: str = Field(..., min_length=2)
    email:   str

    @field_validator("email")
    @classmethod
    def validate_email_fmt(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class RunAgentResponse(BaseModel):
    session_id:     str
    status:         str
    signals:        dict[str, Any] = {}
    research_brief: str = ""
    email_subject:  str = ""
    email_body:     str = ""
    error:          Optional[str] = None
    chat_history:   list[dict[str, str]] = []


class SessionResponse(BaseModel):
    session_id:  str
    state:       dict[str, Any]
    exists:      bool
