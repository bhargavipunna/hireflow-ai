"""Base class for all job scrapers.

Subclasses implement `parse(html, config)` to extract job dicts from a
page, and optionally `parse_feed(payload)` for JSON feeds. The base
handles fetching (via the shared HTTPClient with retry), graceful
fallback to sample data, normalization into `Job` objects and JSON
persistence.
"""

from __future__ import annotations

import asyncio
import json
import re
from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from app.config.exceptions import ScraperError
from app.config.logger import get_logger
from app.models.job import Job
from app.utils.http_client import get_http_client

log = get_logger(__name__)


class BaseScraper(ABC):
    """Abstract scraper backed by a JSON source config."""

    #: filename stem under config/sources/ (e.g. "wellfound")
    config_name: str = ""

    def __init__(self, source_label: Optional[str] = None):
        if not self.config_name:
            raise ScraperError(
                f"{type(self).__name__} must set `config_name` to a source file stem."
            )
        # Lazy import to avoid a circular dependency at module load time.
        from app.scrapers.source_config import load_source

        self.source = source_label or self.config_name
        self.config = load_source(self.config_name)
        self.http = get_http_client()

    # --- hooks subclasses may override -------------------------------------
    def parse(self, html: str, config: dict) -> list[dict]:
        """Extract job dicts from raw HTML. Default: BS4 with config selectors."""
        return self._parse_with_selectors(html, config)

    def parse_feed(self, payload: Any, config: dict) -> list[dict]:
        """Extract job dicts from a parsed JSON feed. Override if needed."""
        return []

    def endpoints(self) -> list[str]:
        return list(self.config.get("endpoints", []))

    # --- public entry points ----------------------------------------------
    def scrape(self) -> list[Job]:
        """Fetch live jobs, falling back to sample data on failure."""
        jobs_data: list[dict] = []
        try:
            for url in self.endpoints():
                html = self.http.get(url)
                if html:
                    parsed = self.parse(html, self.config)
                    log.info(
                        "[%s] parsed %d jobs from %s",
                        self.source, len(parsed), url,
                    )
                    jobs_data.extend(parsed)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("[%s] scrape raised: %s", self.source, exc)

        if not jobs_data:
            fallback = self.config.get("fallback_jobs", [])
            log.info(
                "[%s] no live jobs; using %d fallback entries",
                self.source, len(fallback),
            )
            jobs_data = list(fallback)

        jobs = [self._to_job(j) for j in jobs_data if self._is_valid(j)]
        return jobs

    async def scrape_async(self) -> list[Job]:
        """Async wrapper around `scrape()` for concurrent collection."""
        return await asyncio.to_thread(self.scrape)

    # --- helpers -----------------------------------------------------------
    def _is_valid(self, raw: dict) -> bool:
        return bool(raw.get("title") and raw.get("company"))

    def _to_job(self, raw: dict) -> Job:
        return Job(
            title=raw.get("title", ""),
            company=raw.get("company", ""),
            location=raw.get("location", "Unknown"),
            description=raw.get("description", ""),
            apply_link=raw.get("apply_link", "") or raw.get("link", "") or "",
            source=self.source,
            job_type=raw.get("job_type", "Full Time"),
            posted_date=raw.get("posted_date", ""),
            salary=raw.get("salary", ""),
            experience=raw.get("experience", ""),
        )

    def _parse_with_selectors(self, html: str, config: dict) -> list[dict]:
        """Best-effort BS4 extraction using config['selectors']."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:  # pragma: no cover
            log.warning("beautifulsoup4 not installed; cannot parse HTML")
            return []

        selectors = config.get("selectors", {}) or {}
        card_sel = selectors.get("job_card")
        if not card_sel:
            return []

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(card_sel)
        if not cards:
            return []

        out: list[dict] = []
        base_url = config.get("base_url", "")
        for card in cards:
            try:
                title = self._text(card.select_one(selectors["title"])) if selectors.get("title") else ""
                company = self._text(card.select_one(selectors["company"])) if selectors.get("company") else ""
                location = self._text(card.select_one(selectors["location"])) if selectors.get("location") else ""
                link_el = card.select_one(selectors["link"]) if selectors.get("link") else None
                link = link_el.get("href", "") if link_el and link_el.has_attr("href") else ""
                if link and base_url and link.startswith("/"):
                    link = base_url + link
                if title and company:
                    out.append({
                        "title": title,
                        "company": company,
                        "location": location or "Unknown",
                        "description": card.get_text(" ", strip=True)[:1500],
                        "apply_link": link,
                    })
            except Exception:
                continue
        return out

    @staticmethod
    def _text(node) -> str:
        return node.get_text(" ", strip=True) if node else ""

    # --- legacy persistence helper (kept for compatibility) ---------------
    def save_jobs(self, jobs: Iterable[Job], filename: str) -> None:
        import os
        os.makedirs("data/jobs", exist_ok=True)
        with open(f"data/jobs/{filename}", "w", encoding="utf-8") as f:
            json.dump([j.to_dict() for j in jobs], f, indent=2, ensure_ascii=False)
