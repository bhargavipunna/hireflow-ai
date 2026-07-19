"""Repository indexing all generated artifacts.

Lets the daily-report agent (and any UI later) enumerate every resume,
cover letter, cold email and report produced by the pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from app.config.settings import DOCS_INDEX_PATH
from app.models.generated_doc import GeneratedDocument
from app.repository.base_repo import BaseRepository


class GeneratedDocumentRepository(BaseRepository[GeneratedDocument]):
    path = Path(DOCS_INDEX_PATH)

    def __init__(self, path=None):
        if path is None:
            path = DOCS_INDEX_PATH
        super().__init__(path)

    def to_dict(self, item: GeneratedDocument) -> dict:
        return item.to_dict()

    def from_dict(self, data: dict) -> GeneratedDocument:
        return GeneratedDocument.from_dict(data)

    def key(self, item: GeneratedDocument) -> str:
        return item.id

    def register(self, doc: GeneratedDocument) -> GeneratedDocument:
        return self.add(doc)

    def register_many(self, docs: Iterable[GeneratedDocument]) -> int:
        return self.add_many(docs)

    def by_type(self, doc_type: str) -> list[GeneratedDocument]:
        return self.filter(lambda d: d.type == doc_type)

    def by_job(self, job_ref: str) -> list[GeneratedDocument]:
        return self.filter(lambda d: d.job_ref == job_ref)

    def latest(self, doc_type: str, job_ref: Optional[str] = None) -> Optional[GeneratedDocument]:
        items = self.by_type(doc_type) if doc_type else self.all()
        if job_ref:
            items = [d for d in items if d.job_ref == job_ref]
        if not items:
            return None
        return max(items, key=lambda d: d.created_at)
