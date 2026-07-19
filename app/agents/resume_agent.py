"""ResumeAgent: generate an ATS-optimized resume per qualified job.

Only jobs at or above the configured threshold get a tailored resume.
Output is written under data/generated_resumes/ and indexed in the
generated-document repository.
"""

from __future__ import annotations

import os

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

    def _prompt(self, job: Job) -> str:
        return f"""
You are an expert ATS Resume Optimizer.

JOB TITLE:
{job.title}

COMPANY:
{job.company}

JOB DESCRIPTION:
{job.description}

RELEVANT RESUME CONTEXT:
{job.retrieved_context}

TASK:
Create an ATS optimized resume draft.

Rules:
1. Never invent experience.
2. Never invent projects.
3. Never invent skills.
4. Reorder content for relevance.
5. Highlight the most relevant projects.
6. Improve ATS keyword coverage.
7. Keep everything truthful.
8. Output resume text only.
9. Never hallucinate candidate details.
10. Never use placeholders.
11. Keep the resume concise and professional.
12. Tailor the resume to the job description.
""".strip()

    def run(self, state: dict) -> dict:
        self.log.info("=== Resume Agent Started ===")
        threshold = state.get("threshold", MATCH_THRESHOLD)
        qualified = [j for j in self.jobs_from_state(state) if j.score >= threshold]
        self.log.info(
            "Generating resumes for %d/%d jobs (threshold %.1f)",
            len(qualified), len(self.jobs_from_state(state)), threshold,
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
