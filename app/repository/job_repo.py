"""Repository for scraped + matched jobs.

Two files are maintained:
- raw_jobs.json     : every job discovered by scrapers (deduped)
- matched_jobs.json : jobs that passed the score threshold + retrieved context
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.config.settings import JOBS_DIR, MATCHED_JOBS_PATH, RAW_JOBS_PATH
from app.models.job import Job
from app.repository.base_repo import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Stores raw scraped jobs at RAW_JOBS_PATH."""

    path = Path(RAW_JOBS_PATH)

    def __init__(self, path=None):
        if path is None:
            path = RAW_JOBS_PATH
        super().__init__(path)

    # --- hooks ---
    def to_dict(self, item: Job) -> dict:
        return item.to_dict()

    def from_dict(self, data: dict) -> Job:
        return Job.from_dict(data)

    def key(self, item: Job) -> str:
        return item.id

    # --- helpers ---
    def save_raw(self, jobs: Iterable[Job]) -> int:
        return self.add_many(jobs)

    def by_source(self, source: str) -> list[Job]:
        return self.filter(lambda j: j.source == source.lower())


class MatchedJobRepository(BaseRepository[Job]):
    """Stores matched (scored) jobs at MATCHED_JOBS_PATH."""

    path = Path(MATCHED_JOBS_PATH)

    def __init__(self, path=None):
        if path is None:
            path = MATCHED_JOBS_PATH
        super().__init__(path)

    def to_dict(self, item: Job) -> dict:
        return item.to_dict()

    def from_dict(self, data: dict) -> Job:
        return Job.from_dict(data)

    def key(self, item: Job) -> str:
        return item.id

    def save_matched(self, jobs: Iterable[Job]) -> int:
        self.clear()
        return self.add_many(jobs)

    def top(self, limit: int = 10) -> list[Job]:
        return sorted(self.all(), key=lambda j: j.score, reverse=True)[:limit]
