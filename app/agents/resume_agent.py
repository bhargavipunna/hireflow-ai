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
from app.services.resume_source_service import ResumeSourceService


class ResumeAgent(BaseAgent):
    name = "resume"

    def __init__(self):
        super().__init__()
        self.llm = LLMService()
        self.resume_source = ResumeSourceService()
        # Lazy-loaded: some tests construct ResumeAgent without ChromaDB.
        self._retriever = None
        self._identity_cache: str | None = None
        os.makedirs("data/generated_resumes", exist_ok=True)

    @property
    def retriever(self):
        if self._retriever is None:
            from app.rag.retriever import Retriever
            self._retriever = Retriever()
        return self._retriever

    def _fetch_identity(self) -> str:
        """Deterministically retrieve the candidate's name/contact line.

        Semantic retrieval is query-dependent — a skills-focused JD may
        not surface the resume header chunk. So we issue a dedicated
        query that reliably ranks the header first, then cache the
        result for the whole run.
        """
        if self._identity_cache is not None:
            return self._identity_cache
        try:
            chunks = self.retriever.retrieve(
                "candidate name email phone contact linkedin github address"
            )
            context = "\n".join(chunks)
            self._identity_cache = self._extract_identity(context)
        except Exception as exc:
            self.log.warning("Identity retrieval failed: %s", exc)
            self._identity_cache = ""
        return self._identity_cache

    @staticmethod
    def _extract_identity(context: str) -> str:
        """Pull candidate name + contact line from anywhere in the context.

        Strategy: find the contact line (contains @ and .com/.in), then
        treat the immediately preceding short line as the candidate name.
        This is more reliable than pattern-matching names, which produces
        false positives on lines like job titles.
        """
        lines = [l.strip() for l in context.split("\n") if l.strip()]

        email_idx = -1
        for i, line in enumerate(lines):
            if "@" in line and (".com" in line or ".in" in line):
                email_idx = i
                break
        if email_idx == -1:
            return ""

        email_line = lines[email_idx]
        # Walk backwards from the contact line to find a plausible name.
        name_line = ""
        for j in range(email_idx - 1, max(-1, email_idx - 4), -1):
            candidate = lines[j]
            words = candidate.split()
            if (
                2 <= len(words) <= 4
                and not candidate.startswith(("•", "-", "*", "|", "_", "#", "(", "htt"))
                and "@" not in candidate
                and not any(ch.isdigit() for ch in candidate)
            ):
                name_line = candidate
                break

        parts = [p for p in (name_line, email_line) if p]
        return "\n".join(parts)

    def _prompt(self, job: Job) -> str:
        # Try the job's retrieved context first; fall back to a dedicated
        # identity query so we always know the real candidate.
        identity = self._extract_identity(job.retrieved_context)
        if not identity:
            identity = self._fetch_identity()
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

    def _latex_prompt(self, job: Job, template: str) -> str:
        identity = self._extract_identity(job.retrieved_context)
        if not identity:
            identity = self._fetch_identity()
        identity_block = ""
        if identity:
            identity_block = f"""
CANDIDATE IDENTITY (you MUST preserve these exact details):
{identity}
"""

        return f"""
You are an expert ATS resume editor and LaTeX resume maintainer.

JOB TITLE:
{job.title}

COMPANY:
{job.company}

JOB DESCRIPTION:
{job.description}
{identity_block}
CANDIDATE FACTS RETRIEVED FROM THE REAL RESUME:
{job.retrieved_context}

MASTER LATEX RESUME SOURCE:
```tex
{template}
```

TASK:
Create a tailored duplicate of the master LaTeX resume for this job.

CRITICAL RULES:
1. Return ONLY complete LaTeX source code. No markdown fences, no commentary.
2. Preserve the original candidate identity and contact details.
3. Preserve the LaTeX document structure and commands unless a small edit is needed.
4. Use ONLY facts, projects, skills, education, and achievements present in the candidate facts or master source.
5. Do NOT invent companies, metrics, titles, dates, links, skills, or experience.
6. Reorder and rewrite bullets to emphasize the strongest truthful match to this job.
7. Add ATS keywords only when they truthfully match the candidate's existing skills.
8. Keep the resume concise and one-resume focused.
""".strip()

    @staticmethod
    def _clean_latex_output(content: str) -> str:
        cleaned = content.strip()
        fence = re.match(r"^```(?:tex|latex)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        return cleaned

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
                template = self.resume_source.latex_template()
                if template:
                    result = self.llm.generate(self._latex_prompt(job, template))
                    result = self._clean_latex_output(result)
                    extension = "tex"
                    note = "tailored from master LaTeX resume"
                else:
                    result = self.llm.generate(self._prompt(job))
                    extension = "txt"
                    note = ""
            except Exception as exc:
                self.log.error("LLM failed for %s: %s", job.id, exc)
                continue

            stem = self._safe_name(job.company, job.title)
            doc = self.write_resume(stem, result, job.id, extension=extension, note=note)
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
