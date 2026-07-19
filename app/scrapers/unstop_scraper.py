"""Unstop scraper (competitions, hackathons, internships & jobs)."""

from app.scrapers.base_scraper import BaseScraper


class UnstopScraper(BaseScraper):
    config_name = "unstop"

    def __init__(self):
        super().__init__(source_label="unstop")
