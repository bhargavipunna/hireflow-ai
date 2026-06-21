import chromadb

from app.config.settings import (
    CHROMA_PATH,
    COLLECTION_NAME
)


class VectorDB:

    def __init__(self):

        self.client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME
        )

    def add_document(
        self,
        doc_id,
        text,
        embedding
    ):

        self.collection.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding]
        )

    def search(
        self,
        embedding,
        top_k=5
    ):

        return self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k
        )