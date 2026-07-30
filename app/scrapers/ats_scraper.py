"""Public ATS job-feed scraper.

Many companies publish job boards through applicant-tracking systems with
free public JSON feeds. This scraper supports the common ones that do not
require paid APIs: Greenhouse, Lever, Ashby, and SmartRecruiters.
"""

from __future__ import annotations

import re
from html import unescape
from typing import Any

from app.config.logger import get_logger
from app.scrapers.base_scraper import BaseScraper

log = get_logger(__name__)


class ATSScraper(BaseScraper):
    config_name = "ats"

    def __init__(self):
        super().__init__(source_label="ats")

    def endpoints(self) -> list[str]:
        return []

    def scrape(self):  # type: ignore[override]
        jobs_data: list[dict] = []
        for board in self.config.get("boards", []):
            provider = board.get("provider", "").lower()
            company = board.get("company", "")
            token = board.get("token", "")
            if not provider or not token:
                continue
            url = self._feed_url(provider, token)
            if not url:
                continue
            try:
                payload = self.http.get_json(url)
                if payload:
                    jobs_data.extend(self._parse_provider(provider, payload, company))
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("[ats] %s/%s failed: %s", provider, company or token, exc)

        if not jobs_data:
            fallback = self.config.get("fallback_jobs", [])
            log.info("[ats] using %d fallback entries", len(fallback))
            jobs_data = list(fallback)

        return [self._to_job(j) for j in jobs_data if self._is_valid(j)]

    @staticmethod
    def _feed_url(provider: str, token: str) -> str:
        if provider == "greenhouse":
            return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        if provider == "lever":
            return f"https://api.lever.co/v0/postings/{token}?mode=json"
        if provider == "ashby":
            return f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        if provider == "smartrecruiters":
            return f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100"
        return ""

    def _parse_provider(self, provider: str, payload: Any, company: str) -> list[dict]:
        if provider == "greenhouse":
            return self._parse_greenhouse(payload, company)
        if provider == "lever":
            return self._parse_lever(payload, company)
        if provider == "ashby":
            return self._parse_ashby(payload, company)
        if provider == "smartrecruiters":
            return self._parse_smartrecruiters(payload, company)
        return []

    def _parse_greenhouse(self, payload: dict, company: str) -> list[dict]:
        out = []
        for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
            location = item.get("location") or {}
            out.append({
                "title": item.get("title", ""),
                "company": company,
                "location": location.get("name", "Unknown") if isinstance(location, dict) else "Unknown",
                "description": self._clean_html(item.get("content", ""))[:1500],
                "apply_link": item.get("absolute_url", ""),
                "job_type": "Full Time",
                "posted_date": item.get("updated_at", ""),
            })
        return out

    def _parse_lever(self, payload: list, company: str) -> list[dict]:
        out = []
        for item in payload if isinstance(payload, list) else []:
            categories = item.get("categories") or {}
            location = categories.get("location") or item.get("workplaceType") or "Unknown"
            description = "\n".join(
                str(section.get("content", ""))
                for section in item.get("lists", []) or []
                if isinstance(section, dict)
            )
            out.append({
                "title": item.get("text", ""),
                "company": company,
                "location": location,
                "description": self._clean_html(description or item.get("descriptionPlain", ""))[:1500],
                "apply_link": item.get("hostedUrl", ""),
                "job_type": categories.get("commitment", "Full Time"),
                "posted_date": str(item.get("createdAt", "")),
            })
        return out

    def _parse_ashby(self, payload: dict, company: str) -> list[dict]:
        out = []
        for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
            location = item.get("location") or "Unknown"
            if isinstance(location, dict):
                location = location.get("name", "Unknown")
            out.append({
                "title": item.get("title", ""),
                "company": company,
                "location": location,
                "description": self._clean_html(item.get("descriptionHtml", ""))[:1500],
                "apply_link": item.get("jobUrl", ""),
                "job_type": item.get("employmentType", "Full Time"),
                "posted_date": item.get("publishedAt", ""),
            })
        return out

    def _parse_smartrecruiters(self, payload: dict, company: str) -> list[dict]:
        out = []
        for item in payload.get("content", []) if isinstance(payload, dict) else []:
            location = item.get("location") or {}
            out.append({
                "title": item.get("name", ""),
                "company": company,
                "location": location.get("city", "Unknown") if isinstance(location, dict) else "Unknown",
                "description": self._clean_html(item.get("jobAd", {}).get("sections", {}).get("jobDescription", ""))[:1500],
                "apply_link": item.get("ref", ""),
                "job_type": "Full Time",
                "posted_date": item.get("releasedDate", ""),
            })
        return out

    @staticmethod
    def _clean_html(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value or "")
        return re.sub(r"\s+", " ", unescape(text)).strip()
