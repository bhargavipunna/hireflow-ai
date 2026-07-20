"""Tests for the source-config loader and scraper manager.

Validates the config-driven architecture without making real HTTP calls
- we test loading + dedupe logic only.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.scrapers.scraper_manager import ScraperManager
from app.scrapers.source_config import load_source


def test_load_source_wellfound():
    cfg = load_source("wellfound")
    assert cfg["name"] == "Wellfound"
    assert "fallback_jobs" in cfg
    assert len(cfg["fallback_jobs"]) >= 1


def test_load_source_missing_raises():
    from app.config.exceptions import ConfigError
    with pytest.raises(ConfigError):
        load_source("does_not_exist_xyz")


def test_all_sources_have_required_fields():
    from app.scrapers.source_config import load_all_sources

    sources = load_all_sources()
    assert len(sources) >= 7  # wellfound, internshala, unstop, mnc, startup, remote, company
    for stem, cfg in sources.items():
        assert "name" in cfg, f"{stem} missing 'name'"
        assert "enabled" in cfg, f"{stem} missing 'enabled'"


def test_scraper_manager_dedupe_logic():
    """Dedupe is pure - testable without HTTP."""
    from app.models.job import Job

    jobs = [
        Job(title="AI Engineer", company="Acme", location="R", description="a",
            apply_link="", source="s", job_type="FT", posted_date=""),
        Job(title="AI Engineer", company="Acme", location="R", description="b",
            apply_link="", source="s", job_type="FT", posted_date=""),  # dup
        Job(title="Eng", company="Other", location="R", description="c",
            apply_link="", source="s", job_type="FT", posted_date=""),
    ]
    deduped = ScraperManager._dedupe(jobs)
    assert len(deduped) == 2
