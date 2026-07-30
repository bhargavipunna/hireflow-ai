"""Resolve the candidate resume source.

The app prefers a master LaTeX resume when available, because that lets
the resume agent duplicate and tailor the actual source file instead of
inventing a separate markdown document. PDF remains the fallback for the
existing RAG workflow.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.config.settings import (
    MASTER_RESUME_TEX_PATH,
    MASTER_RESUME_TEX_URL,
    RESUME_DIR,
    RESUME_PATH,
)


@dataclass(frozen=True)
class ResumeSource:
    path: Path
    kind: str
    text: str
    fingerprint: str


class ResumeSourceService:
    """Select and load the best available resume source."""

    def resolve(self) -> ResumeSource:
        tex_path = self._resolve_tex_path()
        if tex_path and tex_path.exists():
            text = tex_path.read_text(encoding="utf-8")
            return ResumeSource(
                path=tex_path,
                kind="latex",
                text=text,
                fingerprint=self._fingerprint(text),
            )

        if RESUME_PATH.exists():
            return ResumeSource(
                path=RESUME_PATH,
                kind="pdf",
                text="",
                fingerprint=self._file_fingerprint(RESUME_PATH),
            )

        raise FileNotFoundError(
            f"No resume source found. Add {MASTER_RESUME_TEX_PATH} or {RESUME_PATH}."
        )

    def has_latex_template(self) -> bool:
        try:
            return self.resolve().kind == "latex"
        except FileNotFoundError:
            return False

    def latex_template(self) -> str:
        source = self.resolve()
        if source.kind != "latex":
            return ""
        return source.text

    def _resolve_tex_path(self) -> Path | None:
        if MASTER_RESUME_TEX_URL:
            return self._download_tex(MASTER_RESUME_TEX_URL)
        return MASTER_RESUME_TEX_PATH

    def _download_tex(self, url: str) -> Path:
        parsed = urlparse(url)
        if parsed.netloc.endswith("overleaf.com") and "/project/" in parsed.path:
            raise FileNotFoundError(
                "Overleaf project URLs are editor pages, not direct .tex files. "
                "Export the .tex source to data/resume/resume.tex or use an Overleaf "
                "Git URL only if your account includes that premium feature."
            )

        RESUME_DIR.mkdir(parents=True, exist_ok=True)
        name = Path(parsed.path).name or "resume.tex"
        if not name.endswith(".tex"):
            name = "resume.tex"
        target = RESUME_DIR / name
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type.lower():
            raise FileNotFoundError(
                f"{url} returned HTML, not LaTeX source. Use a direct .tex URL."
            )
        target.write_text(response.text, encoding="utf-8")
        return target

    @staticmethod
    def _fingerprint(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _file_fingerprint(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
