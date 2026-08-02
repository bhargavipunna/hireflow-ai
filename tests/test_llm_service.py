import pytest

from app.config.exceptions import LLMServiceError
from app.services.llm_service import LLMService


class _Provider:
    def __init__(self, name, result=None, available=True):
        self.name = name
        self.result = result
        self._available = available
        self.calls = 0

    def available(self):
        return self._available

    def generate(self, prompt):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_llm_service_uses_first_available_provider():
    first = _Provider("first", "ok")
    second = _Provider("second", "later")
    service = LLMService(providers=[first, second])

    assert service.generate("prompt") == "ok"
    assert first.calls == 1
    assert second.calls == 0


def test_llm_service_falls_back_after_failure(monkeypatch):
    monkeypatch.setattr("app.services.llm_service.LLM_RETRIES", 1)
    first = _Provider("first", RuntimeError("quota"))
    second = _Provider("second", "fallback")
    service = LLMService(providers=[first, second])

    assert service.generate("prompt") == "fallback"
    assert first.calls == 1
    assert second.calls == 1


def test_llm_service_skips_unconfigured_provider():
    first = _Provider("first", "nope", available=False)
    second = _Provider("second", "ok")
    service = LLMService(providers=[first, second])

    assert service.generate("prompt") == "ok"
    assert first.calls == 0
    assert second.calls == 1


def test_llm_service_raises_when_all_fail(monkeypatch):
    monkeypatch.setattr("app.services.llm_service.LLM_RETRIES", 1)
    service = LLMService(providers=[_Provider("first", RuntimeError("down"))])

    with pytest.raises(LLMServiceError, match="All LLM providers failed"):
        service.generate("prompt")
