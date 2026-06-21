from app.services.embedding_service import (
    EmbeddingService
)

from sklearn.metrics.pairwise import (
    cosine_similarity
)


class ScoreService:

    def __init__(self):

        self.embedder = EmbeddingService()

    def calculate_score(
        self,
        resume_text,
        job_description
    ):

        resume_embedding = (
            self.embedder.embed(
                resume_text
            )
        )

        job_embedding = (
            self.embedder.embed(
                job_description
            )
        )

        score = cosine_similarity(
            [resume_embedding],
            [job_embedding]
        )[0][0]

        return round(
            score * 100,
            2
        )