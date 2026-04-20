"""
FireReach – Database Connection & Initialization
Manages SQLAlchemy engine and session factory for PostgreSQL (Neon).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import logging

from utils.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
DATABASE_URL = settings.database_url

# Create SQLAlchemy engine
# NullPool: don't maintain a persistent pool (good for serverless/Neon)
# pool_pre_ping: test connection before using it
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency injection for FastAPI - get DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables.
    Call this on application startup.
    """
    try:
        # Import Base after engine is created to avoid circular imports
        from services.database_models import Base

        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise
