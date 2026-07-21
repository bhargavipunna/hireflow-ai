"""ATSScorerAgent: estimate ATS fitness of the tailored resume vs the JD.

This is a heuristic + LLM hybrid:
1. Keyword overlap between the generated resume and the JD.
2. An optional LLM judgment for structure/clarity (gracefully skipped
   if the LLM is unavailable).

The resulting ats_score is attached to the matched job and persisted.
"""

from __future__ import annotations

import re
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.config.logger import get_logger
from app.models.job import Job
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.services.llm_service import LLMService

log = get_logger(__name__)

STOPWORDS = {
    "the", "and", "for", "with", "you", "are", "our", "will", "this", "that",
    "have", "from", "your", "into", "their", "they", "but", "not", "who",
    "what", "when", "where", "how", "why", "all", "any", "can", "may", "etc",
}


class ATSScorerAgent(BaseAgent):
    name = "ats_scorer"

    def __init__(self):
        super().__init__()
        self.docs_repo = GeneratedDocumentRepository()
        try:
            self.llm = LLMService()
        except Exception:  # pragma: no cover
            self.llm = None

    # --- keyword overlap ---------------------------------------------------
    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            t.lower()
            for t in re.findall(r"[A-Za-z][A-Za-z0-9+#.]*", text)
            if len(t) > 2 and t.lower() not in STOPWORDS
        }

    @staticmethod
    def keyword_score(resume_text: str, jd_text: str) -> float:
        jd_tokens = ATSScorerAgent._tokens(jd_text)
        if not jd_tokens:
            return 0.0
        resume_tokens = ATSScorerAgent._tokens(resume_text)
        overlap = jd_tokens & resume_tokens
        return round(100.0 * len(overlap) / len(jd_tokens), 2)

    # --- optional LLM judgment --------------------------------------------
    def llm_score(self, resume_text: str, jd_text: str) -> Optional[float]:
        if not self.llm:
            return None
        prompt = (
            "You are an ATS scoring engine. Given a resume and a job description, "
            "return ONLY a single integer 0-100 representing keyword coverage and "
            "fitness. No prose.\n\n"
            f"RESUME:\n{resume_text[:2500]}\n\n"
            f"JOB DESCRIPTION:\n{jd_text[:1500]}\n\nSCORE:"
        )
        try:
            raw = self.llm.generate(prompt)
            m = re.search(r"\b(\d{1,3})\b", raw)
            if m:
                val = float(m.group(1))
                return max(0.0, min(100.0, val))
        except Exception as exc:
            log.warning("LLM ATS score failed: %s", exc)
        return None

    # --- entry -------------------------------------------------------------
    def run(self, state: dict) -> dict:
        self.log.info("=== ATS Scorer Agent Started ===")
        qualified = self.qualified_jobs(state)
        scored = 0

        for job in qualified:
            resume_doc = self.docs_repo.latest("resume", job.id)
            if not resume_doc:
                continue
            try:
                with open(resume_doc.path, "r", encoding="utf-8") as f:
                    resume_text = f.read()
            except OSError as exc:
                self.log.warning("Cannot read resume %s: %s", resume_doc.path, exc)
                continue

            kw = self.keyword_score(resume_text, job.description)
            lm = self.llm_score(resume_text, job.description)
            final = round(0.6 * kw + 0.4 * lm, 2) if lm is not None else kw
            job.ats_score = final

            self.matched_repo.update(job.id, lambda j: self._set(j, final))
            self.log.info(
                "ATS score %.1f (kw=%.1f%s) for %s @ %s",
                final, kw, f", llm={lm}" if lm is not None else "", job.title, job.company,
            )
            scored += 1

        state["ats_scored"] = scored
        return state

    @staticmethod
    def _set(job: Job, ats_score: float) -> Job:
        job.ats_score = ats_score
        return job
