"""Centralized application configuration.

All values are environment-driven with sensible defaults so the app runs
out of the box (e.g. on a fresh checkout) while remaining configurable.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


# --- Paths -----------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
LOG_DIR = BASE_DIR / os.getenv("LOG_DIR", "logs")
REPORT_DIR = DATA_DIR / "reports"
GENERATED_RESUME_DIR = DATA_DIR / "generated_resumes"
COVER_LETTER_DIR = DATA_DIR / "cover_letters"
EMAIL_DIR = DATA_DIR / "emails"
SOURCES_DIR = BASE_DIR / "config" / "sources"

RESUME_PATH = DATA_DIR / "resume" / "resume.pdf"
JOBS_DIR = DATA_DIR / "jobs"
RAW_JOBS_PATH = JOBS_DIR / "raw_jobs.json"
MATCHED_JOBS_PATH = JOBS_DIR / "matched_jobs.json"
APPLICATIONS_PATH = DATA_DIR / "applications.json"
DOCS_INDEX_PATH = DATA_DIR / "docs_index.json"

CHROMA_PATH = str(DATA_DIR / os.getenv("CHROMA_DIR_REL", "chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "user_profile")
TOP_K = _env_int("TOP_K", 5)

# --- LLM / Embeddings ------------------------------------------------------
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")

# --- Matching --------------------------------------------------------------
MATCH_THRESHOLD = _env_int("MATCH_THRESHOLD", 65)
TOP_MATCHES = _env_int("TOP_MATCHES", 10)

# --- Scraper behavior ------------------------------------------------------
SCRAPER_TIMEOUT = _env_int("SCRAPER_TIMEOUT", 20)
SCRAPER_RETRIES = _env_int("SCRAPER_RETRIES", 3)
SCRAPER_BACKOFF = float(os.getenv("SCRAPER_BACKOFF", "1.5"))
SCRAPER_CONCURRENCY = _env_int("SCRAPER_CONCURRENCY", 5)
SCRAPER_ENABLED_SOURCES = [
    s.strip()
    for s in os.getenv("SCRAPER_ENABLED_SOURCES", "").split(",")
    if s.strip()
] or None  # None => all enabled

# --- Outbound actions (always draft-only by default) -----------------------
SEND_EMAILS = _env_bool("SEND_EMAILS", False)  # reserved; stays False in Phase 1
AUTO_APPLY = _env_bool("AUTO_APPLY", False)    # reserved; stays False in Phase 1


def ensure_dirs() -> None:
    """Create all required directories if missing."""
    for path in (
        DATA_DIR,
        LOG_DIR,
        REPORT_DIR,
        GENERATED_RESUME_DIR,
        COVER_LETTER_DIR,
        EMAIL_DIR,
        JOBS_DIR,
        SOURCES_DIR,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)
