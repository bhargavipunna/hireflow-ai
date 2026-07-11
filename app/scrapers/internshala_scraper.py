from app.scrapers.base_scraper import BaseScraper
from app.models.job import Job


class InternshalaScraper(BaseScraper):

    def __init__(self):
        super().__init__("Internshala")

    def scrape(self):

        jobs = [

            Job(
                title="Python Intern",

                company="TechVision",

                location="Hyderabad",

                description="""
                            Python
                            Flask
                            APIs
                            SQL
                            """,

                apply_link="https://example.com/intern",

                source="internshala",

                job_type="Internship",

                posted_date="Today"
            )

        ]

        return jobs