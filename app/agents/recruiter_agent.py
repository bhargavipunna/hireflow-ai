"""RecruiterAgent: infer a plausible recruiter contact for each company.

This is deterministic and conservative - it does NOT scrape individual
people. Given a company name it derives:
- a normalized domain (company.com),
- a plausible careers page,
- a generic recruiter email pattern (careers@ / talent@ / hiring@).

These are *guesses* intended only to seed cold-email drafts. Real
recruiter lookup (LinkedIn etc.) is a Phase-2 concern and would need
explicit opt-in due to TOS / privacy considerations.
"""

from __future__ import annotations

import re

from app.agents.base_agent import BaseAgent
from app.models.job import Job

# Common suffixes stripped when guessing a domain.
COMPANY_SUFFIXES = (
    "inc", "inc.", "llc", "ltd", "ltd.", "co", "corp", "corporation",
    "pvt", "pvt.", "limited", "technologies", "technology", "labs",
    "software", "systems", "solutions", "ai", "the",
)

EMAIL_PREFIXES = ("careers", "talent", "hiring", "recruiting", "jobs")


class RecruiterAgent(BaseAgent):
    name = "recruiter"

    @staticmethod
    def _slug(company: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9 ]", "", company.lower()).strip()
        tokens = [t for t in slug.split() if t and t not in COMPANY_SUFFIXES]
        if not tokens:
            return slug.replace(" ", "")
        # Heuristic: take the first meaningful token (often the brand).
        return tokens[0]

    def derive(self, company: str) -> dict:
        slug = self._slug(company) or "company"
        domain = f"{slug}.com"
        email = f"{EMAIL_PREFIXES[0]}@{domain}"
        return {
            "recruiter_name": f"{company} Talent Team",
            "recruiter_email": email,
            "domain": domain,
            "careers_url": f"https://{domain}/careers",
        }

    def run(self, state: dict) -> dict:
        self.log.info("=== Recruiter Agent Started ===")
        qualified = self.qualified_jobs(state)

        for job in qualified:
            info = self.derive(job.company)
            job.recruiter_name = info["recruiter_name"]
            job.recruiter_email = info["recruiter_email"]
            self.matched_repo.update(job.id, lambda j, i=info: self._apply(j, i))
            self.log.debug("Inferred %s for %s", info["recruiter_email"], job.company)

        state["recruiters_filled"] = len(qualified)
        return state

    @staticmethod
    def _apply(job: Job, info: dict) -> Job:
        job.recruiter_name = info["recruiter_name"]
        job.recruiter_email = info["recruiter_email"]
        return job
