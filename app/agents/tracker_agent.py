"""TrackerAgent: maintain the application tracker.

For every qualified job, upsert an Application record that accumulates
references to the resume, cover letter and cold email produced upstream.
This is the canonical "what have I applied to / drafted" store that the
daily report and any future dashboard read from.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.models.application import Application
from app.repository.application_repo import ApplicationRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository


class TrackerAgent(BaseAgent):
    name = "tracker"

    def __init__(self):
        super().__init__()
        self.app_repo = ApplicationRepository()
        self.docs_repo = GeneratedDocumentRepository()

    def run(self, state: dict) -> dict:
        self.log.info("=== Tracker Agent Started ===")
        qualified = self.qualified_jobs(state)
        updated = 0

        for job in qualified:
            resume = self.docs_repo.latest("resume", job.id)
            cover = self.docs_repo.latest("cover_letter", job.id)
            email = self.docs_repo.latest("cold_email", job.id)

            # Determine the furthest status reached.
            if email is not None:
                status = "ready_for_review"
            elif cover is not None:
                status = "cover_letter_generated"
            elif resume is not None:
                status = "resume_generated"
            else:
                status = "matched"

            app = Application(
                job_id=job.id,
                company=job.company,
                title=job.title,
                status=status,
                score=job.score,
                apply_link=job.apply_link,
                source=job.source,
                resume_path=resume.path if resume else "",
                cover_letter_path=cover.path if cover else "",
                email_path=email.path if email else "",
            )
            self.app_repo.upsert(app)
            updated += 1

        state["applications"] = [a.to_dict() for a in self.app_repo.all()]
        self.log.info(
            "Tracker now holds %d applications", len(self.app_repo.all())
        )
        return state
