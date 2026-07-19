"""Loader for declarative scraper source configs under config/sources/*.json.

Each config has a uniform shape:
{
  "name": str,
  "enabled": bool,
  "base_url": str,
  "endpoints": [str],
  "selectors": {...},
  "fallback_jobs": [...],     # used when live fetch yields nothing
  "companies": [{name, careers_url}],  # for multi-company scrapers
  "feeds": [{name, url}]              # for feed-based scrapers
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.config.exceptions import ConfigError
from app.config.logger import get_logger
from app.config.settings import SOURCES_DIR

log = get_logger(__name__)


def load_source(name: str) -> dict:
    """Load a single source config by name (without .json)."""
    path = SOURCES_DIR / f"{name}.json"
    if not path.exists():
        raise ConfigError(f"Source config not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except ValueError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc


def load_all_sources() -> dict[str, dict]:
    """Load every source config keyed by filename stem."""
    if not SOURCES_DIR.exists():
        log.warning("Sources dir missing: %s", SOURCES_DIR)
        return {}
    sources = {}
    for path in sorted(SOURCES_DIR.glob("*.json")):
        try:
            sources[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            log.error("Skipping invalid source config %s: %s", path, exc)
    return sources
