"""Data models for the job agent."""

from app.models.application import Application, STATUS_PIPELINE
from app.models.generated_doc import GeneratedDocument, DOC_TYPES
from app.models.job import Job

__all__ = [
    "Application",
    "STATUS_PIPELINE",
    "GeneratedDocument",
    "DOC_TYPES",
    "Job",
]
