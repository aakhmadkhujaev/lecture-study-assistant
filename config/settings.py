"""Environment-backed application settings."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    storage_root: Path
    database_path: Path
    ai_api_key: str | None
    ai_model: str = ""
    openai_api_key: str | None = None
    ai_chunk_threshold: int = 40000


def get_settings() -> Settings:
    """Load application settings from the environment and optional .env file."""
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_API_KEY") or None
    return Settings(
        storage_root=Path(os.getenv("STORAGE_ROOT", "./data")),
        database_path=Path(
            os.getenv("DATABASE_PATH", "./data/lecture_study_assistant.db")
        ),
        ai_api_key=openai_api_key,
        openai_api_key=openai_api_key,
        ai_model=os.getenv("AI_MODEL", ""),
        ai_chunk_threshold=int(os.getenv("AI_CHUNK_THRESHOLD", "40000")),
    )
