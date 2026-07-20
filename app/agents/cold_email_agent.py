"""ColdEmailAgent: draft a personalized cold email to a recruiter.

IMPORTANT: This agent NEVER sends email. It only writes a draft to
data/emails/. Real SMTP sending is gated behind the (default-off)
SEND_EMAILS flag and is not implemented in Phase 1.

The draft references the inferred recruiter (from RecruiterAgent) and
the candidate's relevant context to produce a tight, specific outreach.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.config.settings import SEND_EMAILS
from app.models.job import Job
from app.services.llm_service import LLMService


class ColdEmailAgent(BaseAgent):
    name = "cold_email"

    def __init__(self):
        super().__init__()
        self.llm = LLMService()

    def _prompt(self, job: Job) -> str:
        return f"""
Write a short, specific cold outreach email for a job application.

TO: {job.recruiter_email or "talent@" + job.company.lower().replace(" ", "") + ".com"}
RECRUITER: {job.recruiter_name or "Hiring Team"}
COMPANY: {job.company}
ROLE: {job.title}

JOB DESCRIPTION:
{job.description}

CANDIDATE'S ACTUAL PROFILE (use ONLY this — never invent):
{job.retrieved_context}

Output format (plain text, no markdown):

Subject: <a single compelling line>

<body of 3 short paragraphs:
 - 1 line hook referencing the company / role
 - 2 concrete, quantified achievements from the REAL candidate context mapped to the JD
 - a soft ask: quick chat / referral>

CRITICAL RULES:
1. NEVER invent achievements not in the candidate's real context.
2. NEVER fabricate a candidate name — use the real name from the context.
3. Do not include greetings like "Dear Sir/Madam".
4. Keep under 150 words.
5. Do NOT use placeholders.
""".strip()

    def run(self, state: dict) -> dict:
        self.log.info("=== Cold Email Agent Started ===")
        if SEND_EMAILS:
            self.log.warning(
                "SEND_EMAILS is set but Phase 1 never sends - writing drafts only."
            )

        qualified = self.qualified_jobs(state)
        produced = []

        for job in qualified:
            try:
                result = self.llm.generate(self._prompt(job))
            except Exception as exc:
                self.log.error("LLM failed for %s: %s", job.id, exc)
                continue
            stem = self._safe_name(job.company, job.title)
            doc = self.write_cold_email(stem, result, job.id)
            self.track(job, "email_drafted", email_path=doc.path)
            produced.append(doc.to_dict())

        state["cold_emails"] = produced
        return state
