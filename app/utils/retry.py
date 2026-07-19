"""Retry helpers built on `tenacity`.

Provides a reusable decorator with exponential backoff for transient
failures (network, parsing). Falls back gracefully if `tenacity` is not
installed by becoming a pass-through.
"""

from __future__ import annotations

import functools
from typing import Callable, Type

try:
    from tenacity import (
        Retrying,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    _HAS_TENACITY = True
except ImportError:  # pragma: no cover - tenacity is listed in requirements
    _HAS_TENACITY = False


def make_retrying(
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    multiplier: float = 1.5,
    max_wait: float = 10.0,
) -> "Retrying | None":
    """Return a configured `Retrying` iterator, or None if tenacity missing."""
    if not _HAS_TENACITY:
        return None
    return Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )


def with_retry(
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
    max_attempts: int = 3,
    multiplier: float = 1.5,
):
    """Decorator: retry the wrapped callable on the given exceptions."""

    def decorator(func: Callable):
        if not _HAS_TENACITY:
            return func

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retryer = make_retrying(
                exceptions=exceptions,
                max_attempts=max_attempts,
                multiplier=multiplier,
            )
            assert retryer is not None
            for attempt in retryer:
                with attempt:
                    return func(*args, **kwargs)

        return wrapper

    return decorator
