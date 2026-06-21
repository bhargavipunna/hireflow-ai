import json

from app.services.score_service import ScoreService
from app.rag.retriever import Retriever


class MatcherAgent:

    def __init__(self):

        self.scorer = ScoreService()

        self.retriever = Retriever()

    def run(self, state):

        jobs = state["jobs"]

        matched_jobs = []

        for job in jobs:

            relevant_chunks = (
                self.retriever.retrieve(
                    job["description"]
                )
            )

            context = "\n".join(
                relevant_chunks
            )

            score = (
                self.scorer.calculate_score(
                    context,
                    job["description"]
                )
            )

            matched_jobs.append(
            {
                "title": job["title"],

                "company": job["company"],

                "location": job.get(
                    "location",
                    "Unknown"
                ),

                "source": job.get(
                    "source",
                    "Unknown"
                ),

                "apply_link": job.get(
                    "apply_link",
                    ""
                ),

                "description":
                job["description"],

                "score":
                score,

                "retrieved_context":
                context
            }
        )

        matched_jobs.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        state["matched_jobs"] = (
            matched_jobs
        )

        with open(
            "data/jobs/matched_jobs.json",
            "w"
        ) as f:

            json.dump(
                matched_jobs,
                f,
                indent=4
            )

        return state