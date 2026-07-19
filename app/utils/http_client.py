"""Shared HTTP client with retry, rotating User-Agents and graceful failure.

All scrapers should fetch through this client rather than calling
`requests` directly. On failure it logs and returns `None` so scrapers
can fall back to sample data without crashing the whole run.
"""

from __future__ import annotations

import random
from typing import Optional

from app.config.logger import get_logger
from app.config.settings import SCRAPER_BACKOFF, SCRAPER_RETRIES, SCRAPER_TIMEOUT
from app.utils.retry import make_retrying

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:  # pragma: no cover - requests is in requirements
    requests = None  # type: ignore[assignment]
    RequestException = Exception  # type: ignore[misc]

log = get_logger(__name__)

USER_AGENTS = [
    # Desktop Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Desktop Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 "
    "Firefox/125.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class HTTPClient:
    """Thin wrapper around `requests` with retry + UA rotation."""

    def __init__(
        self,
        timeout: int = SCRAPER_TIMEOUT,
        max_retries: int = SCRAPER_RETRIES,
        backoff: float = SCRAPER_BACKOFF,
    ):
        if requests is None:  # pragma: no cover
            raise RuntimeError(
                "The 'requests' package is required for HTTPClient. "
                "Install dependencies via `pip install -r requirements.txt`."
            )
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _headers(self, extra: Optional[dict] = None) -> dict:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        if extra:
            headers.update(extra)
        return headers

    def get(self, url: str, extra_headers: Optional[dict] = None) -> Optional[str]:
        """GET a URL and return text on success, or None on failure."""
        retryer = make_retrying(
            exceptions=(RequestException,),
            max_attempts=self.max_retries,
            multiplier=self.backoff,
        )
        try:
            assert retryer is not None
            for attempt in retryer:
                with attempt:
                    response = self._session.get(
                        url,
                        headers=self._headers(extra_headers),
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    return response.text
        except RequestException as exc:
            log.warning("GET failed for %s: %s", url, exc)
        except AssertionError:
            # tenacity not installed - do a single attempt
            try:
                response = self._session.get(
                    url,
                    headers=self._headers(extra_headers),
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.text
            except RequestException as exc:
                log.warning("GET failed for %s: %s", url, exc)
        return None

    def get_json(self, url: str, extra_headers: Optional[dict] = None):
        """GET a URL and parse JSON. Returns dict/list or None."""
        text = self.get(url, extra_headers=extra_headers)
        if text is None:
            return None
        try:
            import json

            return json.loads(text)
        except ValueError as exc:
            log.warning("JSON parse failed for %s: %s", url, exc)
            return None


# Shared singleton - import this rather than constructing new clients.
_shared: Optional[HTTPClient] = None


def get_http_client() -> HTTPClient:
    global _shared
    if _shared is None:
        _shared = HTTPClient()
    return _shared
