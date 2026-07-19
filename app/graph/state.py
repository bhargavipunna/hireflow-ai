"""Workflow state.

TypedDict consumed by every node in the LangGraph pipeline. Optional
fields default to sensible values inside each agent, so callers may pass
a minimal state.
"""

from __future__ import annotations

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # Inputs
    resume_text: str
    threshold: float

    # Scraping
    jobs: list[dict]

    # Matching
    matched_jobs: list[dict]
    top_matches: list[dict]

    # Generated artifacts (lists of GeneratedDocument dicts)
    resumes: list[dict]
    cover_letters: list[dict]
    cold_emails: list[dict]
    ats_scored: int
    recruiters_filled: int

    # Tracker + reporting
    applications: list[dict]
    report_path: str
