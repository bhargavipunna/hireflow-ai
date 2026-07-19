"""Shared scraper utilities.

Kept for backward compatibility with existing scrapers; the real HTTP
plumbing now lives in `app.utils.http_client`.
"""

from app.utils.http_client import USER_AGENTS  # noqa: F401  (re-export)


def get_random_headers():
    """Return a headers dict with a random User-Agent."""
    import random

    return {"User-Agent": random.choice(USER_AGENTS)}
