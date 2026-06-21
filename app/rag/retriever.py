from app.rag.vectordb import VectorDB
from app.services.embedding_service import EmbeddingService

from app.config.settings import TOP_K


class Retriever:

    def __init__(self):

        self.db = VectorDB()

        self.embedder = EmbeddingService()

    def retrieve(
        self,
        query
    ):

        query_embedding = self.embedder.embed(
            query
        )

        results = self.db.search(
            query_embedding,
            TOP_K
        )


        return results["documents"][0]

    def retrieve(self, query):

        query_embedding = (
            self.embedder.embed(query)
        )

        results = self.db.search(
            query_embedding,
            TOP_K
        )

        print("\nRETRIEVED CHUNKS")
        print("=" * 50)

        for doc in results["documents"][0]:
            print(doc[:150])
            print()

        return results["documents"][0]