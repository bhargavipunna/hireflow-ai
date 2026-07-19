"""Startup career-page scraper.

Mirrors `MNCScraper` but for startup career boards (Greenhouse, Lever,
Ashby, Workable, etc.). The shared BS4 parser handles generic markup;
fallback sample startups cover the dry-run case.
"""

from app.scrapers.base_scraper import BaseScraper


class StartupScraper(BaseScraper):
    config_name = "startup"

    def __init__(self):
        super().__init__(source_label="startup")

    def endpoints(self) -> list[str]:
        return [c["careers_url"] for c in self.config.get("companies", []) if c.get("careers_url")]
