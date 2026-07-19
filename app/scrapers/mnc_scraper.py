"""MNC career-page scraper.

Iterates over `companies` in the source config, fetches each careers
page, and extracts jobs via the shared selector-based parser. Falls back
to the sample MNC jobs if all live fetches fail.
"""

from __future__ import annotations

from app.config.logger import get_logger
from app.scrapers.base_scraper import BaseScraper

log = get_logger(__name__)


class MNCScraper(BaseScraper):
    config_name = "mnc"

    def __init__(self):
        super().__init__(source_label="mnc")

    def endpoints(self) -> list[str]:
        # Each company's careers_url becomes an endpoint; company name is
        # attached so the parser can label the job correctly.
        return [c["careers_url"] for c in self.config.get("companies", []) if c.get("careers_url")]

    def parse(self, html: str, config: dict) -> list[dict]:
        # Use the base selector parser, then re-label company from config.
        parsed = self._parse_with_selectors(html, config)
        # Determine which company this html belongs to based on URL is not
        # available here; the manager records source as 'mnc'. The
        # company name in the card text takes precedence, but if missing
        # we leave it for _to_job to flag invalid.
        return parsed
