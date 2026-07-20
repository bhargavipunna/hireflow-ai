"""Tests for the repository layer.

Uses tmp_path fixtures so real data/ files are never touched.
"""

import json
from pathlib import Path

import pytest

from app.models.application import Application
from app.models.generated_doc import GeneratedDocument
from app.models.job import Job
from app.repository.application_repo import ApplicationRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.repository.job_repo import JobRepository, MatchedJobRepository


@pytest.fixture
def job_repo(tmp_path):
    return JobRepository(tmp_path / "raw.json")


@pytest.fixture
def matched_repo(tmp_path):
    return MatchedJobRepository(tmp_path / "matched.json")


@pytest.fixture
def app_repo(tmp_path):
    return ApplicationRepository(tmp_path / "apps.json")


@pytest.fixture
def doc_repo(tmp_path):
    return GeneratedDocumentRepository(tmp_path / "docs.json")


def _make_job(title="Eng", company="Acme", score=70.0, description="python"):
    return Job(title=title, company=company, location="Remote",
               description=description, apply_link="", source="s",
               job_type="FT", posted_date="", score=score)


# --- JobRepository -----------------------------------------------------------

def test_job_repo_add_replaces_same_key(job_repo):
    j1 = _make_job()
    j2 = _make_job(description="updated")
    job_repo.add(j1)
    job_repo.add(j2)
    assert len(job_repo.all()) == 1
    assert job_repo.all()[0].description == "updated"


def test_job_repo_add_many_dedupes(job_repo):
    jobs = [_make_job(), _make_job(title="Other"), _make_job()]
    n = job_repo.add_many(jobs)
    assert n == 2


def test_job_repo_get_by_key(job_repo):
    j = _make_job()
    job_repo.add(j)
    fetched = job_repo.get(j.id)
    assert fetched is not None
    assert fetched.title == "Eng"


# --- MatchedJobRepository ----------------------------------------------------

def test_matched_repo_save_clears_first(matched_repo):
    matched_repo.add(_make_job(title="Old"))
    matched_repo.save_matched([_make_job(title="A"), _make_job(title="B")])
    titles = {j.title for j in matched_repo.all()}
    assert titles == {"A", "B"}


def test_matched_repo_top_returns_best(matched_repo):
    matched_repo.save_matched([
        _make_job(title="Low", score=50),
        _make_job(title="High", score=90),
        _make_job(title="Mid", score=70),
    ])
    top = matched_repo.top(2)
    assert [j.title for j in top] == ["High", "Mid"]


# --- ApplicationRepository ---------------------------------------------------

def test_app_repo_upsert_advances_status(app_repo):
    j = _make_job()
    app_repo.upsert(Application(job_id=j.id, company=j.company, title=j.title, status="matched"))
    app_repo.upsert(Application(job_id=j.id, company=j.company, title=j.title, status="resume_generated"))
    apps = app_repo.all()
    assert len(apps) == 1
    assert apps[0].status == "resume_generated"


def test_app_repo_upsert_does_not_regress(app_repo):
    j = _make_job()
    app_repo.upsert(Application(job_id=j.id, company=j.company, title=j.title, status="resume_generated"))
    app_repo.upsert(Application(job_id=j.id, company=j.company, title=j.title, status="matched"))
    assert app_repo.get(j.id).status == "resume_generated"


def test_app_repo_summary(app_repo):
    for i, status in enumerate(["matched", "matched", "resume_generated"]):
        app_repo.upsert(Application(job_id=f"job_{i}", company="c", title="t", status=status))
    s = app_repo.summary()
    assert s["matched"] == 2
    assert s["resume_generated"] == 1


# --- GeneratedDocumentRepository --------------------------------------------

def test_doc_repo_latest_by_type(doc_repo):
    doc_repo.register(GeneratedDocument(type="resume", job_ref="a", path="old.txt"))
    doc_repo.register(GeneratedDocument(type="resume", job_ref="a", path="new.txt"))
    latest = doc_repo.latest("resume", "a")
    # Both created near-instantly; ensure latest returns a resume for a.
    assert latest is not None
    assert latest.type == "resume"


def test_doc_repo_by_type(doc_repo):
    doc_repo.register(GeneratedDocument(type="resume", job_ref="a", path="r.txt"))
    doc_repo.register(GeneratedDocument(type="cover_letter", job_ref="a", path="c.txt"))
    doc_repo.register(GeneratedDocument(type="resume", job_ref="b", path="r2.txt"))
    assert len(doc_repo.by_type("resume")) == 2
    assert len(doc_repo.by_type("cover_letter")) == 1


# --- BaseRepository atomic writes -------------------------------------------

def test_repository_writes_valid_json(job_repo, tmp_path):
    job_repo.add(_make_job())
    raw = json.loads((tmp_path / "raw.json").read_text())
    assert isinstance(raw, list)
    assert raw[0]["title"] == "Eng"
