"""Retriever: semantic search over the candidate's resume chunks.

Wraps ChromaDB query with the shared embedding service and surfaces the
top-K most relevant chunks for a given job description.
"""

from __future__ import annotations

from app.config.logger import get_logger
from app.config.settings import TOP_K
from app.rag.vectordb import VectorDB
from app.services.embedding_service import EmbeddingService

log = get_logger(__name__)


class Retriever:
    def __init__(self):
        self.db = VectorDB()
        self.embedder = EmbeddingService()

    def retrieve(self, query: str, top_k: int = TOP_K) -> list[str]:
        query_embedding = self.embedder.embed(query)
        results = self.db.search(query_embedding, top_k)
        docs = results["documents"][0] if results.get("documents") else []

        if docs:
            log.debug("Retrieved %d chunks for query", len(docs))
        return docs
