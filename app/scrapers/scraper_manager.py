from app.scrapers.wellfound_scraper import WellfoundScraper
from app.scrapers.internshala_scraper import InternshalaScraper
from app.scrapers.company_scraper import CompanyScraper


class ScraperManager:

    def __init__(self):

        self.scrapers = [

            WellfoundScraper(),

            InternshalaScraper(),

            CompanyScraper()

        ]

    def collect_jobs(self):

        all_jobs = []

        for scraper in self.scrapers:

            print(f"\nRunning {scraper.source} scraper...")

            jobs = scraper.scrape()

            print(f"Collected {len(jobs)} jobs")

            all_jobs.extend(jobs)

        return all_jobs