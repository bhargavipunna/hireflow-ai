"""Remote job-board scraper.

Consumes JSON feeds (e.g. RemoteOK) and RSS feeds (e.g. WeWorkRemotely)
declared in the source config. JSON feeds are parsed directly; RSS feeds
are parsed with a lightweight regex extractor to avoid extra deps.
Falls back to the sample remote jobs if every feed fails.
"""

from __future__ import annotations

import re
from typing import Any

from app.config.logger import get_logger
from app.scrapers.base_scraper import BaseScraper

log = get_logger(__name__)

_ITEM_RE = re.compile(r"<item>(.*?)</item>", re.DOTALL)
_FIELD_RES = {
    "title": re.compile(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", re.DOTALL),
    "link": re.compile(r"<link>(.*?)</link>", re.DOTALL),
    "description": re.compile(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", re.DOTALL),
}


class RemoteScraper(BaseScraper):
    config_name = "remote"

    def __init__(self):
        super().__init__(source_label="remote")

    def endpoints(self) -> list[str]:
        # RemoteScraper iterates over feeds, not plain endpoints.
        return []

    def scrape(self):  # type: ignore[override]
        jobs_data: list[dict] = []
        for feed in self.config.get("feeds", []):
            url = feed.get("url", "")
            if not url:
                continue
            try:
                if url.endswith(".json") or "remoteok.com/api" in url:
                    payload = self.http.get_json(url)
                    if payload:
                        jobs_data.extend(self.parse_feed(payload, self.config))
                else:
                    text = self.http.get(url)
                    if text:
                        jobs_data.extend(self._parse_rss(text))
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("[remote] feed %s failed: %s", url, exc)

        if not jobs_data:
            fallback = self.config.get("fallback_jobs", [])
            log.info("[remote] using %d fallback entries", len(fallback))
            jobs_data = list(fallback)

        return [self._to_job(j) for j in jobs_data if self._is_valid(j)]

    def parse_feed(self, payload: Any, config: dict) -> list[dict]:
        """RemoteOK-style API: a list whose first element is a legend object."""
        if not isinstance(payload, list):
            return []
        # Skip the first element if it looks like a metadata object.
        items = payload[1:] if payload and isinstance(payload[0], dict) and "slug" in payload[0] else payload
        out: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            company = item.get("company_name") or item.get("company") or ""
            title = item.get("position") or item.get("title") or ""
            if not title or not company:
                continue
            tags = ", ".join(item.get("tags", []) or [])
            description = item.get("description", "") or tags
            out.append({
                "title": title,
                "company": company,
                "location": item.get("location", "Remote"),
                "description": (description or "")[:1500],
                "apply_link": item.get("url", "") or "",
                "posted_date": item.get("date", ""),
                "job_type": "Full Time",
            })
        return out

    def _parse_rss(self, xml: str) -> list[dict]:
        out: list[dict] = []
        for raw_item in _ITEM_RE.findall(xml):
            fields = {}
            for name, regex in _FIELD_RES.items():
                m = regex.search(raw_item)
                if m:
                    fields[name] = m.group(1).strip()
            title = fields.get("title", "")
            if not title:
                continue
            # Title often looks like "Company: Role (Location)"
            company = ""
            location = "Remote"
            if ":" in title:
                company, title = title.split(":", 1)
                company = company.strip()
                title = title.strip()
            if "(" in title and title.endswith(")"):
                title, loc = title.rsplit("(", 1)
                location = loc.rstrip(")").strip() or location
                title = title.strip()
            # Strip simple HTML from description.
            desc = re.sub(r"<[^>]+>", " ", fields.get("description", "")).strip()
            out.append({
                "title": title,
                "company": company,
                "location": location,
                "description": desc[:1500],
                "apply_link": fields.get("link", ""),
            })
        return out
