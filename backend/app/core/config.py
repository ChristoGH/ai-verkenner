"""Application configuration.

Resolves environment settings, including the configurable root-level content paths
(``PROMPTS_DIR`` and ``SOURCES_FILE``). These live at the repository root, not under
``backend/`` — see docs/TECHNICAL_DESIGN.md. Paths are resolved against the repo root (the
parent of ``backend/``) unless given as absolute paths.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py -> parents[3] == repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Load a .env from the repo root if present (no-op if absent).
load_dotenv(REPO_ROOT / ".env")


def _resolve(path_value: str) -> Path:
    """Resolve a path against the repo root unless it is absolute."""
    p = Path(path_value)
    return p if p.is_absolute() else (REPO_ROOT / p)


class Settings:
    """Plain settings holder (kept simple; no pydantic dependency in Task 001)."""

    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AI Verkenner API")
        self.app_version: str = os.getenv("APP_VERSION", "0.1.0")
        self.service_name: str = "ai-verkenner"
        self.frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

        # Root-level content, configurable. Defaults match the repo layout.
        self.prompts_dir: Path = _resolve(os.getenv("PROMPTS_DIR", "prompts"))
        self.sources_file: Path = _resolve(os.getenv("SOURCES_FILE", "sources/sources.yaml"))

        # Placeholder — SQLite arrives in Task 004.
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data/ai_verkenner.db")


settings = Settings()
