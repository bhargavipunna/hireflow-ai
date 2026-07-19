"""Job model.

A dataclass representing a single scraped job posting, with serialization
helpers so repositories and agents can move Jobs around as plain dicts.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Any


def _clean(text: str) -> str:
    """Collapse whitespace and strip junk characters."""
    if not text:
        return ""
    # Normalize unicode spaces, collapse whitespace runs.
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass
class Job:
    title: str
    company: str
    location: str
    description: str
    apply_link: str
    source: str
    job_type: str
    posted_date: str
    salary: str = ""
    experience: str = ""
    # Optional fields populated later in the pipeline.
    score: float = 0.0
    retrieved_context: str = ""
    ats_score: float = 0.0
    recruiter_name: str = ""
    recruiter_email: str = ""

    def __post_init__(self) -> None:
        self.title = _clean(self.title)
        self.company = _clean(self.company)
        self.location = _clean(self.location)
        self.description = self.description.strip()
        self.source = (self.source or "").lower().strip()

    @property
    def id(self) -> str:
        """Stable identity for dedupe / tracker keys."""
        key = f"{self.company.lower()}::{self.title.lower()}"
        # Keep it filesystem-safe.
        return re.sub(r"[^a-z0-9]+", "_", key).strip("_")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["id"] = self.id
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
