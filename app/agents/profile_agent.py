from app.rag.ingest import ResumeIngestor


class ProfileAgent:

    def __init__(self):
        self.ingestor = ResumeIngestor()

    def run(self, state):

        resume_path = "data/resume/resume.pdf"

        text = self.ingestor.load_resume(
            resume_path
        )

        self.ingestor.ingest(
            resume_path
        )

        state["resume_text"] = text

        return state