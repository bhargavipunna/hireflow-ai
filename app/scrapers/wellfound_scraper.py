from app.scrapers.base_scraper import BaseScraper
from app.models.job import Job


class WellfoundScraper(BaseScraper):

    def __init__(self):
        super().__init__("Wellfound")

    def scrape(self):

        jobs = [

            Job(
                title="AI Engineer",
                company="StartupAI",
                location="Remote",

                description="""
Python
FastAPI
RAG
LangGraph
LLMs
""",

                apply_link="https://example.com/apply",

                source="wellfound",

                job_type="Full Time",

                posted_date="Today"
            ),

            Job(
                title="GenAI Intern",
                company="Future Labs",
                location="Remote",

                description="""
Machine Learning
Deep Learning
Python
Generative AI
""",

                apply_link="https://example.com/apply2",

                source="wellfound",

                job_type="Internship",

                posted_date="Today"
            )

        ]

        return jobs