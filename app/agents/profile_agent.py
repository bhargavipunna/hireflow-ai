"""ProfileAgent: load + ingest the candidate's resume into the RAG store.

Reads the resume PDF at `data/resume/resume.pdf`, extracts text, chunks
it, embeds each chunk, and writes the embeddings into ChromaDB. The text
is also placed on the workflow state for downstream agents.
"""

from __future__ import annotations

from app.agents.base_agent import BaseAgent
from app.config.exceptions import ConfigError
from app.config.settings import RESUME_PATH


class ProfileAgent(BaseAgent):
    name = "profile"

    def __init__(self):
        super().__init__()
        # Lazy import keeps the module light if rag deps are missing.
        from app.rag.ingest import ResumeIngestor

        self.ingestor = ResumeIngestor()

    def run(self, state: dict) -> dict:
        self.log.info("Loading resume from %s", RESUME_PATH)
        if not RESUME_PATH.exists():
            raise ConfigError(f"Resume not found at {RESUME_PATH}")

        text = self.ingestor.load_resume(str(RESUME_PATH))
        self.ingestor.ingest(str(RESUME_PATH))

        state["resume_text"] = text
        self.log.info("Profile ready (%d chars)", len(text))
        return state
