"""Repository for the application tracker (Application model)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.config.settings import APPLICATIONS_PATH
from app.models.application import Application, STATUS_PIPELINE
from app.repository.base_repo import BaseRepository


class ApplicationRepository(BaseRepository[Application]):
    path = Path(APPLICATIONS_PATH)

    def __init__(self, path=None):
        if path is None:
            path = APPLICATIONS_PATH
        super().__init__(path)

    # --- hooks ---
    def to_dict(self, item: Application) -> dict:
        return item.to_dict()

    def from_dict(self, data: dict) -> Application:
        return Application.from_dict(data)

    def key(self, item: Application) -> str:
        return item.job_id  # one application per job

    # --- helpers ---
    def upsert(self, app: Application) -> Application:
        """Insert or merge-update an application by job_id."""
        existing = self.get(app.job_id)
        if existing is None:
            return self.add(app)

        def merge(a: Application) -> Application:
            for attr in (
                "resume_path",
                "cover_letter_path",
                "email_path",
                "score",
                "apply_link",
                "source",
            ):
                value = getattr(app, attr)
                if value:
                    setattr(a, attr, value)
            # Status: keep the later of the two.
            if app.status in STATUS_PIPELINE:
                a.advance_to(app.status)
            a.touch()
            return a

        return self.update(app.job_id, merge) or self.add(app)

    def upsert_many(self, apps: Iterable[Application]) -> int:
        count = 0
        for app in apps:
            self.upsert(app)
            count += 1
        return count

    def by_status(self, status: str) -> list[Application]:
        return self.filter(lambda a: a.status == status)

    def review_queue(self) -> list[Application]:
        return sorted(
            self.by_status("ready_for_review"),
            key=lambda a: a.score,
            reverse=True,
        )

    def set_status(self, job_id: str, status: str, notes: str = "") -> Application | None:
        def mutate(app: Application) -> Application:
            app.advance_to(status)
            if notes:
                app.notes = notes
            app.touch()
            return app

        return self.update(job_id, mutate)

    def summary(self) -> dict[str, int]:
        out = {s: 0 for s in [*STATUS_PIPELINE, "rejected"]}
        for app in self.all():
            out[app.status] = out.get(app.status, 0) + 1
        return out
