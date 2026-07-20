"""ResumeAgent: generate an ATS-optimized resume per qualified job.

Only jobs at or above the configured threshold get a tailored resume.
Output is written under data/generated_resumes/ and indexed in the
generated-document repository.
"""

from __future__ import annotations

import os
import re

from app.agents.base_agent import BaseAgent
from app.config.settings import MATCH_THRESHOLD
from app.models.job import Job
from app.services.llm_service import LLMService


class ResumeAgent(BaseAgent):
    name = "resume"

    def __init__(self):
        super().__init__()
        self.llm = LLMService()
        os.makedirs("data/generated_resumes", exist_ok=True)

    @staticmethod
    def _extract_identity(context: str) -> str:
        """Try to pull candidate name/email from the first lines of context."""
        lines = context.strip().split("\n")
        identity_lines = []
        for line in lines[:10]:
            stripped = line.strip()
            if "@" in stripped and (".com" in stripped or ".in" in stripped):
                identity_lines.append(stripped)
            # First non-empty line that looks like a name (2-4 words, no bullet).
            elif stripped and not stripped.startswith(("•", "-", "*", "|", "_", "#")):
                words = stripped.split()
                if 2 <= len(words) <= 6 and all(w[0].isupper() or w[0].isnumeric() for w in words if w):
                    identity_lines.append(stripped)
            if len(identity_lines) >= 2:
                break
        return "\n".join(identity_lines) if identity_lines else ""

    def _prompt(self, job: Job) -> str:
        identity = self._extract_identity(job.retrieved_context)
        identity_block = ""
        if identity:
            identity_block = f"""
CANDIDATE IDENTITY (you MUST use these exact details):
{identity}
"""

        return f"""
You are an expert ATS Resume Optimizer.

JOB TITLE:
{job.title}

COMPANY:
{job.company}

JOB DESCRIPTION:
{job.description}
{identity_block}
CANDIDATE'S ACTUAL RESUME (use ONLY this information — never invent):
{job.retrieved_context}

TASK:
Rewrite and optimize the candidate's resume for THIS specific job.

CRITICAL RULES:
1. Use the candidate's REAL name and contact info shown above — NOT a generic placeholder.
2. Use ONLY projects, experience, skills, and education from the candidate context.
3. NEVER invent, fabricate, or hallucinate ANY details.
4. Reorder sections so the most relevant content appears first.
5. Highlight the 2-3 most relevant projects for this specific job.
6. Add or emphasize ATS keywords from the job description that already appear in the candidate's real skills.
7. Keep every quantified achievement truthful (the exact numbers from the context).
8. Output a complete resume in markdown format.
9. Do NOT use placeholders like [Your Name] or [Link].
10. Keep the resume concise (under 400 words).
""".strip()

    def run(self, state: dict) -> dict:
        self.log.info("=== Resume Agent Started ===")
        threshold = state.get("threshold", MATCH_THRESHOLD)
        all_qualified = [j for j in self.jobs_from_state(state) if j.score >= threshold]
        qualified = self.qualified_jobs(state)  # capped at TOP_MATCHES
        self.log.info(
            "Generating resumes for top %d of %d qualified jobs (threshold %.1f)",
            len(qualified), len(all_qualified), threshold,
        )

        produced = []
        for job in qualified:
            self.log.info("Generating resume for %s @ %s", job.title, job.company)
            try:
                result = self.llm.generate(self._prompt(job))
            except Exception as exc:
                self.log.error("LLM failed for %s: %s", job.id, exc)
                continue

            stem = self._safe_name(job.company, job.title)
            doc = self.write_resume(stem, result, job.id)
            produced.append(doc.to_dict())

            # Update the matched repo so later agents see the resume path.
            self.matched_repo.update(job.id, lambda j: self._attach_resume(j, doc.path))
            self.track(job, "resume_generated", resume_path=doc.path)

        state["resumes"] = produced
        return state

    @staticmethod
    def _attach_resume(job: Job, path: str) -> Job:
        # Persist path on a side channel via description metadata is messy;
        # instead we rely on the generated-doc repo. Nothing to mutate here.
        return job
