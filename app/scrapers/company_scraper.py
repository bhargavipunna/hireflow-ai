"""Generic company career-page scraper.

Used when only a bare careers URL is known (no per-site adapter). It
attempts to extract job postings via:
1. JSON-LD `<script type="application/ld+json">` JobPosting nodes
2. The shared BS4 selector parser

Returns an empty list if nothing is found (no fallback data here - the
source config for 'company' ships with none).
"""

from __future__ import annotations

import json

from app.scrapers.base_scraper import BaseScraper


class CompanyScraper(BaseScraper):
    config_name = "company"

    def __init__(self):
        super().__init__(source_label="company")

    def endpoints(self) -> list[str]:
        return list(self.config.get("endpoints", []))

    def parse(self, html: str, config: dict) -> list[dict]:
        # Try JSON-LD JobPosting nodes first - many ATS systems emit them.
        ld_jobs = self._parse_jsonld(html)
        if ld_jobs:
            return ld_jobs
        # Fall back to selector-based parsing.
        return self._parse_with_selectors(html, config)

    @staticmethod
    def _parse_jsonld(html: str) -> list[dict]:
        from bs4 import BeautifulSoup

        out: list[dict] = []
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(tag.string or "{}")
            except (ValueError, TypeError):
                continue
            blocks = data if isinstance(data, list) else [data]
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("@type") == "JobPosting":
                    out.append({
                        "title": block.get("title", ""),
                        "company": (block.get("hiringOrganization") or {}).get("name", ""),
                        "location": ((block.get("jobLocation") or {}).get("address") or {}).get("addressLocality", "Unknown"),
                        "description": block.get("description", "")[:1500],
                        "apply_link": (block.get("url") or ""),
                    })
        return out
