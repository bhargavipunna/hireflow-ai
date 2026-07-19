"""ScraperAgent: thin agent wrapper around ScraperManager.

Collects jobs from every enabled source and writes them onto the state
as plain dicts. Raw jobs are also persisted via the JobRepository.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.scrapers.scraper_manager import ScraperManager


class ScraperAgent(BaseAgent):
    name = "scraper"

    def __init__(self):
        super().__init__()
        self.manager = ScraperManager()

    def run(self, state: dict) -> dict:
        self.log.info("Collecting jobs from all sources...")
        jobs = self.manager.collect_jobs()
        state["jobs"] = [j.to_dict() for j in jobs]
        self.log.info("Collected %d jobs", len(jobs))
        return state
