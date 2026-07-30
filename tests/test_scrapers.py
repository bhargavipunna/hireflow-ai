"""Tests for the source-config loader and scraper manager.

Validates the config-driven architecture without making real HTTP calls
- we test loading + dedupe logic only.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.scrapers.scraper_manager import ScraperManager
from app.scrapers.ats_scraper import ATSScraper
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
    assert len(sources) >= 8
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


def test_scraper_manager_reads_runtime_source_filter(monkeypatch):
    monkeypatch.setenv("SCRAPER_ENABLED_SOURCES", "ats")
    mgr = ScraperManager()
    assert [s.source for s in mgr.scrapers] == ["ats"]


def test_ats_scraper_parses_greenhouse_payload():
    scraper = ATSScraper()
    jobs = scraper._parse_greenhouse(
        {
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "location": {"name": "Remote"},
                    "content": "<p>Python and APIs</p>",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "updated_at": "2026-01-01",
                }
            ]
        },
        "Acme",
    )
    assert jobs[0]["title"] == "Backend Engineer"
    assert jobs[0]["company"] == "Acme"
    assert jobs[0]["description"] == "Python and APIs"


def test_ats_scraper_parses_lever_payload():
    scraper = ATSScraper()
    jobs = scraper._parse_lever(
        [
            {
                "text": "ML Intern",
                "categories": {"location": "Bangalore", "commitment": "Internship"},
                "lists": [{"content": "<li>PyTorch experiments</li>"}],
                "hostedUrl": "https://jobs.lever.co/acme/1",
            }
        ],
        "Acme",
    )
    assert jobs[0]["title"] == "ML Intern"
    assert jobs[0]["job_type"] == "Internship"
    assert "PyTorch" in jobs[0]["description"]
