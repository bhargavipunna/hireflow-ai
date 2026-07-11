from abc import ABC, abstractmethod
import json
import os

from app.models.job import Job


class BaseScraper(ABC):
    """
    Base class for all job scrapers.
    Every scraper should inherit from this class.
    """

    def __init__(self, source: str):
        self.source = source

    @abstractmethod
    def scrape(self) -> list[Job]:
        """
        Returns a list of Job objects.
        """
        pass

    def save_jobs(self, jobs: list[Job], filename: str):
        """
        Save scraped jobs as JSON.
        """

        os.makedirs("data/jobs", exist_ok=True)

        with open(
            f"data/jobs/{filename}",
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                [job.__dict__ for job in jobs],
                f,
                indent=4,
                ensure_ascii=False
            )