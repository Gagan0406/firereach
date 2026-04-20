"""
FireReach – FastAPI Application
Entry point. Registers routes, CORS, startup validation.
"""
from __future__ import annotations

import sys
import os

# Ensure backend root is in path for imports
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from utils.config import get_settings
from services.database import init_db

settings = get_settings()

app = FastAPI(
    title="FireReach API",
    description="Autonomous AI-powered outreach system. Signal → Research → Personalized Email.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React dev server and production origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://firereach-frontend-zeta.vercel.app",
        "https://firereach-frontend-a7lsghjmo-gagan0406s-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under /api/v1
app.include_router(router, prefix="/api/v1", tags=["FireReach Agent"])


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize database, validate env, and pre-warm the agent graph."""
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database init warning: {e}")

    from agent import get_agent_graph
    try:
        get_agent_graph()
        print("✅ FireReach agent graph initialized")
    except Exception as e:
        print(f"⚠️  Agent graph init warning: {e}")


@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "service": "FireReach",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
