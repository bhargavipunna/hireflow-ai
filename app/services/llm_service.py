"""LLM provider router.

The public interface stays intentionally small: agents call
`LLMService.generate(prompt)`. The router tries configured providers in
order, skipping providers without credentials and falling back on quota,
rate-limit, network, or backend failures.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

import ollama
import requests

from app.config.exceptions import ConfigError, LLMServiceError
from app.config.logger import get_logger
from app.config.settings import (
    LLM_PROVIDER_ORDER,
    LLM_RETRIES,
    NVIDIA_API_KEY,
    NVIDIA_BASE_URL,
    NVIDIA_MODEL,
    OLLAMA_MODEL,
    SARVAM_API_KEY,
    SARVAM_BASE_URL,
    SARVAM_MODEL,
)

log = get_logger(__name__)


class LLMProvider(Protocol):
    name: str

    def available(self) -> bool:
        ...

    def generate(self, prompt: str) -> str:
        ...


@dataclass
class OllamaProvider:
    model: str = OLLAMA_MODEL
    name: str = "ollama"

    def available(self) -> bool:
        return bool(self.model)

    def generate(self, prompt: str) -> str:
        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]


@dataclass
class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible chat-completion APIs."""

    name: str
    api_key: str
    model: str
    base_url: str
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer "

    def available(self) -> bool:
        return bool(self.api_key and self.model and self.base_url)

    def generate(self, prompt: str) -> str:
        headers = {
            "Content-Type": "application/json",
            self.auth_header: f"{self.auth_prefix}{self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=90,
        )
        self._raise_for_retryable(response)
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMServiceError(f"{self.name} returned an unexpected response") from exc

    def _raise_for_retryable(self, response: requests.Response) -> None:
        if response.status_code in {401, 403}:
            raise ConfigError(f"{self.name} API key was rejected")
        if response.status_code in {402, 408, 409, 429, 500, 502, 503, 504}:
            raise LLMServiceError(
                f"{self.name} failed with HTTP {response.status_code}: {response.text[:200]}"
            )
        response.raise_for_status()


class SarvamProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="sarvam",
            api_key=SARVAM_API_KEY,
            model=SARVAM_MODEL,
            base_url=SARVAM_BASE_URL,
            auth_header="api-subscription-key",
            auth_prefix="",
        )


class NvidiaProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="nvidia",
            api_key=NVIDIA_API_KEY,
            model=NVIDIA_MODEL,
            base_url=NVIDIA_BASE_URL,
        )


class LLMService:
    def __init__(self, providers: list[LLMProvider] | None = None):
        self.providers = providers or self._providers_from_settings()

    def generate(self, prompt: str) -> str:
        errors: list[str] = []
        for provider in self.providers:
            if not provider.available():
                log.info("Skipping LLM provider %s: not configured", provider.name)
                continue
            for attempt in range(1, max(1, LLM_RETRIES) + 1):
                try:
                    result = provider.generate(prompt)
                    log.info("LLM provider %s succeeded", provider.name)
                    return result
                except Exception as exc:
                    errors.append(f"{provider.name}: {exc}")
                    log.warning(
                        "LLM provider %s failed (attempt %d/%d): %s",
                        provider.name,
                        attempt,
                        max(1, LLM_RETRIES),
                        exc,
                    )
                    if attempt < max(1, LLM_RETRIES):
                        time.sleep(min(2 ** (attempt - 1), 4))
        raise LLMServiceError("All LLM providers failed: " + " | ".join(errors))

    @staticmethod
    def _providers_from_settings() -> list[LLMProvider]:
        registry: dict[str, LLMProvider] = {
            "ollama": OllamaProvider(),
            "nvidia": NvidiaProvider(),
            "sarvam": SarvamProvider(),
        }
        providers = []
        for name in LLM_PROVIDER_ORDER or ["ollama"]:
            provider = registry.get(name)
            if provider is None:
                log.warning("Unknown LLM provider in LLM_PROVIDER_ORDER: %s", name)
                continue
            providers.append(provider)
        return providers or [registry["ollama"]]
