"""Domain-specific exception hierarchy.

Centralized so callers can catch granular failures without relying on
broad built-in exceptions.
"""


class JobAgentError(Exception):
    """Base exception for all errors raised by the job agent."""


class ConfigError(JobAgentError):
    """Raised when configuration is missing or invalid."""


class ScraperError(JobAgentError):
    """Raised when a scraper fails to fetch or parse a source."""


class LLMServiceError(JobAgentError):
    """Raised when the LLM backend fails."""


class EmbeddingError(JobAgentError):
    """Raised when embedding generation fails."""


class RetrievalError(JobAgentError):
    """Raised when vector retrieval fails."""


class RepositoryError(JobAgentError):
    """Raised when a repository read/write fails."""
