"""Wellfound scraper (remote-first startup job board)."""

from app.scrapers.base_scraper import BaseScraper


class WellfoundScraper(BaseScraper):
    config_name = "wellfound"

    def __init__(self):
        super().__init__(source_label="wellfound")
