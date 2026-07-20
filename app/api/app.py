"""FastAPI application exposing read-only access to the Career Copilot's
state plus two action endpoints (scrape, full-run).

Designed to be lightweight and dashboard-friendly: every endpoint
returns plain JSON that a simple frontend can render.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.config.logger import get_logger
from app.config.settings import MATCH_THRESHOLD, TOP_MATCHES, ensure_dirs
from app.repository.application_repo import ApplicationRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.repository.job_repo import JobRepository, MatchedJobRepository

log = get_logger(__name__)

app = FastAPI(
    title="Career Copilot API",
    description="Autonomous AI job-search assistant - REST surface.",
    version="0.3.0",
)

ensure_dirs()


# --- response models --------------------------------------------------------


class StatsResponse(BaseModel):
    raw_jobs: int
    matched_jobs: int
    applications: int
    generated_docs: int
    by_type: dict[str, int]
    application_status: dict[str, int]


class RunResponse(BaseModel):
    ok: bool
    jobs_discovered: int
    jobs_matched: int
    resumes: int
    cover_letters: int
    cold_emails: int
    ats_scored: int
    report_path: Optional[str] = None


# --- endpoints --------------------------------------------------------------


@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "ok", "service": "career-copilot"}


@app.get("/stats", response_model=StatsResponse)
def stats():
    """Aggregate counts across all repositories."""
    jr = JobRepository()
    mr = MatchedJobRepository()
    ar = ApplicationRepository()
    dr = GeneratedDocumentRepository()

    by_type = {t: len(dr.by_type(t)) for t in ("resume", "cover_letter", "cold_email", "report")}
    return StatsResponse(
        raw_jobs=len(jr.all()),
        matched_jobs=len(mr.all()),
        applications=len(ar.all()),
        generated_docs=len(dr.all()),
        by_type=by_type,
        application_status=ar.summary(),
    )


@app.get("/jobs/matched")
def list_matched(limit: int = Query(50, ge=1, le=500)):
    """List matched jobs, highest score first."""
    mr = MatchedJobRepository()
    return [j.to_dict() for j in mr.top(limit)]


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Fetch a single matched job by id."""
    mr = MatchedJobRepository()
    job = mr.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job.to_dict()


@app.get("/applications")
def list_applications(status: Optional[str] = None):
    """List tracked applications, optionally filtered by status."""
    ar = ApplicationRepository()
    apps = ar.by_status(status) if status else ar.all()
    return [a.to_dict() for a in apps]


@app.get("/documents")
def list_documents(doc_type: Optional[str] = None):
    """List generated documents, optionally filtered by type."""
    dr = GeneratedDocumentRepository()
    docs = dr.by_type(doc_type) if doc_type else dr.all()
    # Newest first.
    docs.sort(key=lambda d: d.created_at, reverse=True)
    return [d.to_dict() for d in docs]


@app.get("/report/today")
def today_report():
    """Return today's daily report path (and content if it exists)."""
    dr = GeneratedDocumentRepository()
    today = date.today().isoformat()
    candidates = [d for d in dr.by_type("report") if today in d.path]
    if not candidates:
        raise HTTPException(status_code=404, detail="No report generated today.")
    doc = max(candidates, key=lambda d: d.created_at)
    try:
        content = open(doc.path, "r", encoding="utf-8").read()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Cannot read report: {exc}")
    return {"path": doc.path, "content": content}


# --- action endpoints -------------------------------------------------------


@app.post("/actions/run", response_model=RunResponse)
def trigger_run():
    """Trigger a full pipeline run synchronously. May take minutes."""
    from app.graph.workflow import workflow

    log.info("API: triggered full pipeline run")
    state = {
        "resume_text": "",
        "jobs": [],
        "matched_jobs": [],
        "threshold": float(MATCH_THRESHOLD),
        "top_matches_limit": int(TOP_MATCHES),
    }
    try:
        result = workflow.invoke(state)
    except Exception as exc:
        log.exception("Pipeline failed via API: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return RunResponse(
        ok=True,
        jobs_discovered=len(result.get("jobs", [])),
        jobs_matched=len(result.get("matched_jobs", [])),
        resumes=len(result.get("resumes", [])),
        cover_letters=len(result.get("cover_letters", [])),
        cold_emails=len(result.get("cold_emails", [])),
        ats_scored=result.get("ats_scored", 0),
        report_path=result.get("report_path"),
    )


@app.post("/actions/scrape")
def trigger_scrape(sources: Optional[str] = Query(None)):
    """Trigger scrapers only. Returns counts per source."""
    import os
    if sources:
        os.environ["SCRAPER_ENABLED_SOURCES"] = sources
    from app.scrapers.scraper_manager import ScraperManager

    mgr = ScraperManager()
    jobs = mgr.collect_jobs()
    by_source: dict[str, int] = {}
    for j in jobs:
        by_source[j.source] = by_source.get(j.source, 0) + 1
    return {"ok": True, "total": len(jobs), "by_source": by_source}
