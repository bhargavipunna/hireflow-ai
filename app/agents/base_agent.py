"""Shared base for agents.

Centralizes:
- logger access,
- the per-state job list conventions,
- threshold filtering,
- artifact file writing + repo registration.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from app.config.logger import get_logger
from app.config.settings import (
    COVER_LETTER_DIR,
    EMAIL_DIR,
    GENERATED_RESUME_DIR,
    MATCH_THRESHOLD,
    REPORT_DIR,
    TOP_MATCHES,
)
from app.models.application import Application
from app.models.generated_doc import GeneratedDocument
from app.models.job import Job
from app.repository.application_repo import ApplicationRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.repository.job_repo import MatchedJobRepository


class BaseAgent:
    """Common helpers for every agent in the pipeline."""

    name: str = "base"

    def __init__(self):
        self.log = get_logger(f"agent.{self.name}")
        self.docs_repo = GeneratedDocumentRepository()
        self.matched_repo = MatchedJobRepository()

    # --- state conventions -------------------------------------------------
    def jobs_from_state(self, state: dict) -> list[Job]:
        """Normalize state['matched_jobs'] into a list of Job objects."""
        raw = state.get("matched_jobs", []) or []
        jobs: list[Job] = []
        for item in raw:
            if isinstance(item, Job):
                jobs.append(item)
            elif isinstance(item, dict):
                jobs.append(Job.from_dict(item))
        return jobs

    def qualified_jobs(self, state: dict, threshold: int | None = None, limit: int | None = None) -> list[Job]:
        """Return only jobs at or above the threshold, capped at *limit*.

        Jobs are defensively re-sorted by score (descending) so callers
        always receive the best matches first, regardless of how the
        state was assembled.
        """
        thr = threshold if threshold is not None else state.get("threshold", MATCH_THRESHOLD)
        cap = limit if limit is not None else state.get("top_matches_limit", TOP_MATCHES)
        jobs = [j for j in self.jobs_from_state(state) if j.score >= thr]
        jobs.sort(key=lambda j: j.score, reverse=True)
        return jobs[:cap]

    def write_state_jobs(self, state: dict, key: str, jobs: Iterable[Job]) -> None:
        state[key] = [j.to_dict() for j in jobs]

    # --- artifact writing --------------------------------------------------
    def _safe_name(self, *parts: str) -> str:
        raw = "_".join(str(p) for p in parts if p)
        return re.sub(r"[^a-zA-Z0-9]+", "_", raw).strip("_")[:120]

    def write_artifact(
        self,
        directory: Path,
        filename_stem: str,
        content: str,
        doc_type: str,
        job_ref: str,
        note: str = "",
    ) -> GeneratedDocument:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{filename_stem}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        doc = GeneratedDocument(
            type=doc_type,
            job_ref=job_ref,
            path=str(path),
            note=note,
        )
        self.docs_repo.register(doc)
        self.log.info("Wrote %s -> %s", doc_type, path)
        return doc

    def write_resume(self, stem: str, content: str, job_ref: str) -> GeneratedDocument:
        return self.write_artifact(
            GENERATED_RESUME_DIR, stem, content, "resume", job_ref
        )

    def write_cover_letter(self, stem: str, content: str, job_ref: str) -> GeneratedDocument:
        return self.write_artifact(
            COVER_LETTER_DIR, stem, content, "cover_letter", job_ref
        )

    def write_cold_email(self, stem: str, content: str, job_ref: str) -> GeneratedDocument:
        return self.write_artifact(
            EMAIL_DIR, stem, content, "cold_email", job_ref
        )

    def write_report(self, stem: str, content: str) -> GeneratedDocument:
        return self.write_artifact(
            REPORT_DIR, stem, content, "report", "", "daily report"
        )

    # --- tracker helper ----------------------------------------------------
    def track(
        self,
        job: Job,
        status: str,
        repo: ApplicationRepository | None = None,
        **extra,
    ) -> Application:
        repo = repo or ApplicationRepository()
        app = Application(
            job_id=job.id,
            company=job.company,
            title=job.title,
            score=job.score,
            apply_link=job.apply_link,
            source=job.source,
            **extra,
        )
        app.status = status  # upsert will advance if appropriate
        return repo.upsert(app)
