"""Application model used by the application tracker.

Represents the lifecycle of one job through the pipeline:
discovered -> matched -> generated artifacts -> human review -> later apply
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any


# Allowed status values, in roughly increasing commitment order.
STATUS_PIPELINE = [
    "discovered",
    "matched",
    "resume_generated",
    "cover_letter_generated",
    "email_drafted",
    "ready_for_review",
    "approved",
    "applied_draft",
    "submitted",
    "reported",
]

TERMINAL_STATUSES = {"rejected"}


@dataclass
class Application:
    job_id: str
    company: str
    title: str
    status: str = "discovered"
    score: float = 0.0
    apply_link: str = ""
    source: str = ""
    resume_path: str = ""
    cover_letter_path: str = ""
    email_path: str = ""
    notes: str = ""
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()

    def advance_to(self, status: str) -> None:
        """Set status if it is later in the pipeline than the current one."""
        if status in TERMINAL_STATUSES:
            self.status = status
            self.touch()
            return
        if status not in STATUS_PIPELINE:
            return
        if self.status in TERMINAL_STATUSES:
            return
        current_idx = (
            STATUS_PIPELINE.index(self.status)
            if self.status in STATUS_PIPELINE
            else -1
        )
        new_idx = STATUS_PIPELINE.index(status)
        if new_idx > current_idx:
            self.status = status
            self.touch()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Application":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
