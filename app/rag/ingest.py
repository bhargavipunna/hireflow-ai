import json
import re
from pathlib import Path

from pypdf import PdfReader

from app.config.settings import RESUME_PROFILE_META_PATH
from app.rag.vectordb import VectorDB
from app.services.embedding_service import EmbeddingService
from app.services.resume_source_service import ResumeSourceService


class ResumeIngestor:

    def __init__(self):

        self.db = VectorDB()

        self.embedder = EmbeddingService()

    def load_resume(self, path):

        suffix = Path(path).suffix.lower()
        if suffix == ".tex":
            return self.load_latex_resume(path)

        reader = PdfReader(path)

        text = ""

        for page in reader.pages:

            text += page.extract_text()

        return text

    def load_latex_resume(self, path):

        raw = Path(path).read_text(encoding="utf-8")
        return self.latex_to_text(raw)

    @staticmethod
    def latex_to_text(source):

        text = re.sub(r"%.*", "", source)
        text = re.sub(r"\\(href|url)\{([^{}]*)\}(?:\{([^{}]*)\})?", r"\2 \3", text)
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", text)
        text = text.replace("\\&", "&")
        text = text.replace("\\%", "%")
        text = text.replace("\\_", "_")
        text = re.sub(r"[{}$]", " ", text)
        text = re.sub(r"\\\\", "\n", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def chunk_text(
    self,
    text,
    chunk_size=800
):

        paragraphs = text.split("\n")

        chunks = []

        current_chunk = ""

        for para in paragraphs:

            if len(
                current_chunk
            ) + len(para) < chunk_size:

                current_chunk += (
                    para + "\n"
                )

            else:

                chunks.append(
                    current_chunk
                )

                current_chunk = (
                    para + "\n"
                )

        if current_chunk:

            chunks.append(
                current_chunk
            )

        return chunks

    def ingest(self, path=None):
        source = ResumeSourceService().resolve() if path is None else None
        source_path = source.path if source else Path(path)
        fingerprint = (
            source.fingerprint
            if source
            else ResumeSourceService._file_fingerprint(source_path)
        )

        meta = self._read_meta()
        current_chunks = self.db.collection.count()
        print(f"Current chunks: {current_chunks}")
        if (
            current_chunks > 0
            and meta.get("fingerprint") == fingerprint
            and meta.get("path") == str(source_path)
        ):
            print("Resume already ingested")
            return

        if current_chunks > 0:
            print("Resume changed; refreshing profile index")
            self.db.clear()

        text = self.load_resume(source_path)

        chunks = self.chunk_text(text)

        for idx, chunk in enumerate(chunks):

            embedding = self.embedder.embed(chunk)

            self.db.add_document(
                doc_id=f"chunk_{idx}",
                text=chunk,
                embedding=embedding
            )

        print(
            f"Ingested {len(chunks)} chunks"
        )
        self._write_meta(source_path, fingerprint, len(chunks))

    def _read_meta(self):

        try:
            return json.loads(RESUME_PROFILE_META_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_meta(self, path, fingerprint, chunk_count):

        RESUME_PROFILE_META_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESUME_PROFILE_META_PATH.write_text(
            json.dumps(
                {
                    "path": str(path),
                    "fingerprint": fingerprint,
                    "chunk_count": chunk_count,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
