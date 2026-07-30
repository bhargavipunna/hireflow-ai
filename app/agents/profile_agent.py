"""ProfileAgent: load + ingest the candidate's resume into the RAG store.

Reads the resume PDF at `data/resume/resume.pdf`, extracts text, chunks
it, embeds each chunk, and writes the embeddings into ChromaDB. The text
is also placed on the workflow state for downstream agents.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.config.exceptions import ConfigError
from app.services.resume_source_service import ResumeSourceService


class ProfileAgent(BaseAgent):
    name = "profile"

    def __init__(self):
        super().__init__()
        # Lazy import keeps the module light if rag deps are missing.
        from app.rag.ingest import ResumeIngestor

        self.ingestor = ResumeIngestor()
        self.resume_source = ResumeSourceService()

    def run(self, state: dict) -> dict:
        try:
            source = self.resume_source.resolve()
        except FileNotFoundError as exc:
            raise ConfigError(str(exc)) from exc

        self.log.info("Loading %s resume from %s", source.kind, source.path)
        text = self.ingestor.load_resume(source.path)
        self.ingestor.ingest(source.path)

        state["resume_text"] = text
        state["resume_source_kind"] = source.kind
        state["resume_source_path"] = str(source.path)
        self.log.info("Profile ready (%d chars)", len(text))
        return state
