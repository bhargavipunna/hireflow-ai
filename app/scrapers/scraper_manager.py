"""ScraperManager: orchestrates all configured scrapers.

- Loads enabled sources from `config/sources/*.json`.
- Instantiates the matching scraper class per source.
- Runs scrapers concurrently (asyncio) with a bounded semaphore.
- Aggregates + dedupes results and persists them via JobRepository.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

from app.config.logger import get_logger
from app.config.settings import SCRAPER_CONCURRENCY, SCRAPER_ENABLED_SOURCES
from app.models.job import Job
from app.repository.job_repo import JobRepository
from app.scrapers.company_scraper import CompanyScraper
from app.scrapers.internshala_scraper import InternshalaScraper
from app.scrapers.mnc_scraper import MNCScraper
from app.scrapers.remote_scraper import RemoteScraper
from app.scrapers.startup_scraper import StartupScraper
from app.scrapers.unstop_scraper import UnstopScraper
from app.scrapers.wellfound_scraper import WellfoundScraper

log = get_logger(__name__)

# Registry: source stem -> scraper class.
SCRAPER_REGISTRY = {
    "wellfound": WellfoundScraper,
    "internshala": InternshalaScraper,
    "unstop": UnstopScraper,
    "mnc": MNCScraper,
    "startup": StartupScraper,
    "remote": RemoteScraper,
    "company": CompanyScraper,
}


class ScraperManager:
    def __init__(self, repo: JobRepository | None = None):
        self.repo = repo or JobRepository()
        self.scrapers = self._init_scrapers()

    def _init_scrapers(self):
        """Instantiate scrapers for enabled sources only."""
        enabled = SCRAPER_ENABLED_SOURCES  # None => all
        scrapers = []
        for stem, cls in SCRAPER_REGISTRY.items():
            if enabled and stem not in enabled:
                continue
            try:
                scrapers.append(cls())
                log.debug("Loaded scraper: %s", stem)
            except Exception as exc:
                log.error("Failed to init scraper %s: %s", stem, exc)
        return scrapers

    def collect_jobs(self) -> list[Job]:
        """Run all scrapers concurrently and return deduped jobs."""
        if not self.scrapers:
            log.warning("No scrapers configured - returning empty job list.")
            return []

        async def run_all() -> list[Job]:
            sem = asyncio.Semaphore(SCRAPER_CONCURRENCY)

            async def bounded(scraper):
                async with sem:
                    return await scraper.scrape_async()

            tasks = [bounded(s) for s in self.scrapers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

        try:
            raw_results = asyncio.run(run_all())
        except RuntimeError:
            # Event loop already running (e.g. inside Jupyter): fall back to sync.
            raw_results = [s.scrape() for s in self.scrapers]

        all_jobs: list[Job] = []
        for scraper, result in zip(self.scrapers, raw_results):
            if isinstance(result, Exception):
                log.warning("[%s] failed: %s", scraper.source, result)
                continue
            all_jobs.extend(result)

        deduped = self._dedupe(all_jobs)
        log.info(
            "Collected %d jobs (%d after dedupe) from %d scrapers",
            len(all_jobs), len(deduped), len(self.scrapers),
        )

        self.repo.save_raw(deduped)
        return deduped

    @staticmethod
    def _dedupe(jobs: Iterable[Job]) -> list[Job]:
        seen: dict[str, Job] = {}
        for job in jobs:
            seen.setdefault(job.id, job)
        return list(seen.values())
