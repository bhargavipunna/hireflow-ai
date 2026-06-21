from app.scrapers.base_scraper import BaseScraper


class InternshalaScraper(BaseScraper):

    def scrape(self):

        return [

            {
                "title": "Python Intern",

                "company": "TechVision",

                "location": "Hyderabad",

                "description":
                """
                Python
                Flask
                APIs
                SQL
                """,

                "apply_link":
                "https://example.com/intern",

                "source":
                "internshala"
            }

        ]