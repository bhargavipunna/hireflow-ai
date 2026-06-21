from pypdf import PdfReader

from app.rag.vectordb import VectorDB
from app.services.embedding_service import EmbeddingService


class ResumeIngestor:

    def __init__(self):

        self.db = VectorDB()

        self.embedder = EmbeddingService()

    def load_resume(self, path):

        reader = PdfReader(path)

        text = ""

        for page in reader.pages:

            text += page.extract_text()

        return text

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

    def ingest(self, path):
        print(
    f"Current chunks: {self.db.collection.count()}"
)
        if self.db.collection.count() > 0:
            print("Resume already ingested")
            return

        text = self.load_resume(path)

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