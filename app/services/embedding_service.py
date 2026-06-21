from sentence_transformers import SentenceTransformer


class EmbeddingService:

    _model = None

    def __init__(self):

        if EmbeddingService._model is None:
            print("Loading embedding model once...")

            EmbeddingService._model = SentenceTransformer(
                "BAAI/bge-small-en-v1.5"
            )

        self.model = EmbeddingService._model

    def embed(self, text):

        return self.model.encode(text).tolist()