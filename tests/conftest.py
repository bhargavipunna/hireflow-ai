"""Shared pytest configuration.

Ensures required data dirs exist for any test that touches the
filesystem-backed repositories, and isolates repo tests from real data
by letting them pass tmp paths.
"""

from pathlib import Path

import pytest

from app.config.settings import ensure_dirs


@pytest.fixture(scope="session", autouse=True)
def _ensure_dirs():
    ensure_dirs()
    yield
