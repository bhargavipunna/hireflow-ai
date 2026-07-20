"""CoverLetterAgent: draft a tailored cover letter per qualified job.

Uses the LLM (Qwen3 via Ollama) and the same retrieved context the
matcher assembled. Output is saved under data/cover_letters/ and indexed
in the generated-document repository.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.models.job import Job
from app.services.llm_service import LLMService


class CoverLetterAgent(BaseAgent):
    name = "cover_letter"

    def __init__(self):
        super().__init__()
        self.llm = LLMService()

    def _prompt(self, job: Job) -> str:
        return f"""
You are an expert cover-letter writer for tech roles.

JOB TITLE: {job.title}
COMPANY: {job.company}
LOCATION: {job.location}

JOB DESCRIPTION:
{job.description}

CANDIDATE'S ACTUAL PROFILE (use ONLY this — never invent):
{job.retrieved_context}

Write a concise, professional cover letter (3 short paragraphs).

CRITICAL RULES:
1. Open with a specific, non-generic hook referencing the company or role.
2. Map 2-3 REAL achievements from the candidate's context to the JD requirements.
3. NEVER invent experience, projects, or skills not present in the candidate's context.
4. NEVER fabricate a candidate name — use the real name from the context.
5. Close with a confident, polite call to action.
6. Output only the letter body (no addresses, no date).
7. Do NOT use placeholders.
""".strip()

    def run(self, state: dict) -> dict:
        self.log.info("=== Cover Letter Agent Started ===")
        qualified = self.qualified_jobs(state)
        self.log.info("Drafting cover letters for %d jobs", len(qualified))

        produced = []
        for job in qualified:
            try:
                result = self.llm.generate(self._prompt(job))
            except Exception as exc:
                self.log.error("LLM failed for %s: %s", job.id, exc)
                continue
            stem = self._safe_name(job.company, job.title)
            doc = self.write_cover_letter(stem, result, job.id)
            self.track(job, "cover_letter_generated", cover_letter_path=doc.path)
            produced.append(doc.to_dict())

        state["cover_letters"] = produced
        return state
