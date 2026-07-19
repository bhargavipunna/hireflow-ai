"""MatcherAgent: scores every scraped job against the resume via RAG.

For each job:
1. Retrieve the most relevant resume chunks from ChromaDB.
2. Compute a cosine-similarity score between the chunks and the JD.
3. Attach score + retrieved context to the job.

High-scoring jobs are persisted to matched_jobs.json via
MatchedJobRepository, and the top-K is surfaced on the state.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.config.settings import MATCH_THRESHOLD, TOP_MATCHES
from app.models.job import Job
from app.rag.retriever import Retriever
from app.services.score_service import ScoreService


class MatcherAgent(BaseAgent):
    name = "matcher"

    def __init__(self):
        super().__init__()
        self.scorer = ScoreService()
        self.retriever = Retriever()

    def _score_one(self, job: Job) -> tuple[float, str]:
        try:
            chunks = self.retriever.retrieve(job.description)
        except Exception as exc:
            self.log.warning("Retrieval failed for %s: %s", job.id, exc)
            chunks = []
        context = "\n".join(chunks)
        score = self.scorer.calculate_score(context, job.description)
        return score, context

    def run(self, state: dict) -> dict:
        raw_jobs = state.get("jobs", []) or []
        jobs = [Job.from_dict(j) if isinstance(j, dict) else j for j in raw_jobs]
        self.log.info("Scoring %d jobs", len(jobs))

        threshold = state.get("threshold", MATCH_THRESHOLD)

        for job in jobs:
            score, context = self._score_one(job)
            job.score = score
            job.retrieved_context = context

        jobs.sort(key=lambda j: j.score, reverse=True)
        qualified = [j for j in jobs if j.score >= threshold]

        self.matched_repo.save_matched(qualified)

        state["matched_jobs"] = [j.to_dict() for j in jobs]
        state["top_matches"] = [j.to_dict() for j in jobs[:TOP_MATCHES]]
        self.log.info(
            "%d jobs met threshold %.1f; top match score %.2f",
            len(qualified), threshold,
            jobs[0].score if jobs else 0.0,
        )
        return state
