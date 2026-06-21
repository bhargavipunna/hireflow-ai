from app.scrapers.base_scraper import BaseScraper


class WellfoundScraper(BaseScraper):

    def scrape(self):

        return [

            {
                "title": "AI Engineer",
                "company": "StartupAI",
                "location": "Remote",

                "description":
                """
                Python
                FastAPI
                RAG
                LangGraph
                LLMs
                """,

                "apply_link":
                "https://example.com/apply",

                "source":
                "wellfound"
            },

            {
                "title": "GenAI Intern",
                "company": "Future Labs",
                "location": "Remote",

                "description":
                """
                Machine Learning
                Deep Learning
                Python
                Generative AI
                """,

                "apply_link":
                "https://example.com/apply2",

                "source":
                "wellfound"
            }

        ]