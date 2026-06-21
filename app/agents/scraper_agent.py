import json

from app.scrapers.wellfound_scraper import (
    WellfoundScraper
)

from app.scrapers.internshala_scraper import (
    InternshalaScraper
)

from app.scrapers.company_scraper import (
    CompanyScraper
)


class ScraperAgent:

    def __init__(self):

        self.scrapers = [

            WellfoundScraper(),

            InternshalaScraper(),

            CompanyScraper()
        ]

    def run(self, state):

        jobs = []

        for scraper in self.scrapers:

            jobs.extend(
                scraper.scrape()
            )

        state["jobs"] = jobs

        with open(
            "data/jobs/raw_jobs.json",
            "w"
        ) as f:

            json.dump(
                jobs,
                f,
                indent=4
            )

        print(
            f"Collected {len(jobs)} jobs"
        )

        return state