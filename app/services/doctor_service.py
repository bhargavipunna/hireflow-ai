"""Preflight checks for local experimentation."""

from __future__ import annotations

import shutil
from dataclasses import dataclass

import ollama

from app.config.settings import (
    LLM_PROVIDER_ORDER,
    NVIDIA_API_KEY,
    OLLAMA_MODEL,
    SARVAM_API_KEY,
)
from app.services.llm_service import LLMService
from app.services.resume_source_service import ResumeSourceService


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
        }


class DoctorService:
    def run(self, test_llm: bool = False) -> list[DoctorCheck]:
        checks = [
            self._resume_source_check(),
            self._ollama_check(),
            self._nvidia_key_check(),
            self._sarvam_key_check(),
            self._latex_compiler_check(),
            self._scraper_config_check(),
        ]
        if test_llm:
            checks.append(self._llm_generation_check())
        return checks

    def _resume_source_check(self) -> DoctorCheck:
        try:
            source = ResumeSourceService().resolve()
            return DoctorCheck(
                "resume_source",
                True,
                f"{source.kind}: {source.path}",
            )
        except Exception as exc:
            return DoctorCheck(
                "resume_source",
                False,
                str(exc),
            )

    def _ollama_check(self) -> DoctorCheck:
        if "ollama" not in LLM_PROVIDER_ORDER:
            return DoctorCheck("ollama", True, "not in LLM_PROVIDER_ORDER")
        try:
            models = ollama.list()
            names = [
                item.get("name") or item.get("model")
                for item in models.get("models", [])
                if isinstance(item, dict)
            ]
            if OLLAMA_MODEL in names:
                return DoctorCheck("ollama", True, f"model available: {OLLAMA_MODEL}")
            return DoctorCheck(
                "ollama",
                False,
                f"Ollama is running but {OLLAMA_MODEL} is not pulled",
            )
        except Exception as exc:
            return DoctorCheck("ollama", False, f"Ollama not reachable: {exc}")

    def _nvidia_key_check(self) -> DoctorCheck:
        if "nvidia" not in LLM_PROVIDER_ORDER:
            return DoctorCheck("nvidia", True, "not in LLM_PROVIDER_ORDER")
        if NVIDIA_API_KEY:
            return DoctorCheck("nvidia", True, "API key configured")
        return DoctorCheck("nvidia", False, "NVIDIA_API_KEY is missing")

    def _sarvam_key_check(self) -> DoctorCheck:
        if "sarvam" not in LLM_PROVIDER_ORDER:
            return DoctorCheck("sarvam", True, "not in LLM_PROVIDER_ORDER")
        if SARVAM_API_KEY:
            return DoctorCheck("sarvam", True, "API key configured")
        return DoctorCheck("sarvam", False, "SARVAM_API_KEY is missing")

    def _latex_compiler_check(self) -> DoctorCheck:
        compiler = next(
            (name for name in ("tectonic", "pdflatex", "xelatex") if shutil.which(name)),
            "",
        )
        if compiler:
            return DoctorCheck("latex_compiler", True, compiler)
        return DoctorCheck(
            "latex_compiler",
            False,
            "No local compiler found; .tex generation works, PDF compilation will be skipped",
        )

    def _scraper_config_check(self) -> DoctorCheck:
        try:
            from app.scrapers.source_config import load_all_sources

            sources = load_all_sources()
            enabled = [name for name, cfg in sources.items() if cfg.get("enabled", True)]
            return DoctorCheck(
                "scraper_config",
                bool(enabled),
                f"{len(enabled)} enabled sources: {', '.join(enabled)}",
            )
        except Exception as exc:
            return DoctorCheck("scraper_config", False, str(exc))

    def _llm_generation_check(self) -> DoctorCheck:
        try:
            result = LLMService().generate("Reply with exactly: ok")
            return DoctorCheck("llm_generation", bool(result.strip()), result.strip()[:120])
        except Exception as exc:
            return DoctorCheck("llm_generation", False, str(exc))
