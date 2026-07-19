"""Internshala scraper (internships & fresher jobs, India)."""

from app.scrapers.base_scraper import BaseScraper


class InternshalaScraper(BaseScraper):
    config_name = "internshala"

    def __init__(self):
        super().__init__(source_label="internshala")
