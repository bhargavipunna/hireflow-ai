import os

from app.services.llm_service import LLMService


class ResumeAgent:
    def __init__(self):

        self.llm = LLMService()

        os.makedirs(
            "data/generated_resumes",
            exist_ok=True
        )

    def run(self, state):
        print("=== Resume Agent Started ===")
        jobs = state["matched_jobs"]

        for job in jobs:
            print(f"Generating resume for {job['title']}")

            prompt = f"""
You are an expert ATS Resume Optimizer.

JOB TITLE:
{job['title']}

COMPANY:
{job['company']}

JOB DESCRIPTION:
{job['description']}

RELEVANT RESUME CONTEXT:
{job['retrieved_context']}

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

"""

            result = self.llm.generate(
                prompt
            )
            print("LLM Response Received")

            filename = (
                f"{job['company']}_{job['title']}"
                .replace(" ", "_")
                .replace("/", "_")
            )

            filepath = (
                f"data/generated_resumes/"
                f"{filename}.txt"
            )

            with open(
                filepath,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(result)

            print(
                f"Generated: {filepath}"
            )

        return state