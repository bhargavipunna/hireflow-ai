"""GeneratedDocument model.

Lightweight index entry for any artifact produced by the pipeline:
resumes, cover letters, cold-email drafts, daily reports.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any

# Allowed document types.
DOC_TYPES = {"resume", "cover_letter", "cold_email", "report", "other"}


@dataclass
class GeneratedDocument:
    type: str
    job_ref: str  # Job.id, or "" for pipeline-wide artifacts like reports
    path: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GeneratedDocument":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
