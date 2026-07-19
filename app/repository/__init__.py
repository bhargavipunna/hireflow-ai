"""Repository layer: JSON-file-backed persistence for jobs, applications,
generated documents, etc.
"""

from app.repository.application_repo import ApplicationRepository
from app.repository.base_repo import BaseRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.repository.job_repo import JobRepository, MatchedJobRepository

__all__ = [
    "ApplicationRepository",
    "BaseRepository",
    "GeneratedDocumentRepository",
    "JobRepository",
    "MatchedJobRepository",
]
