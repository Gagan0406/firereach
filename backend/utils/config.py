"""
FireReach – Application Settings
Reads from .env; never hardcodes secrets.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # LLM
    groq_api_key: str

    # Email
    sendgrid_api_key:  str
    sendgrid_from_email: str = "outreach@firereach.ai"
    sendgrid_from_name:  str = "FireReach"

    # Search / Data
    tavily_api_key: str
    apify_token:    str

    # Database
    database_url: str = ""  # Optional: PostgreSQL connection string

    # App
    log_dir: str = "logs"
    env:     str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
