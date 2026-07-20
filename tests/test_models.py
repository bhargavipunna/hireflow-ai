"""Tests for the data models.

Run with: python -m pytest tests/ -v
"""

import pytest

from app.models.application import Application, STATUS_PIPELINE
from app.models.generated_doc import GeneratedDocument
from app.models.job import Job


# --- Job ---------------------------------------------------------------------

def test_job_post_init_cleans_whitespace():
    j = Job(
        title="  AI   Engineer ",
        company="Acme\tInc",
        location=" Remote ",
        description="Python\n\nRAG",
        apply_link="x",
        source="  WELLFOUND ",
        job_type="Full Time",
        posted_date="today",
    )
    assert j.title == "AI Engineer"
    assert j.company == "Acme Inc"
    assert j.location == "Remote"
    assert j.source == "wellfound"


def test_job_id_is_stable_and_filesystem_safe():
    j1 = Job(title="AI Engineer", company="Acme Inc", location="R",
             description="d", apply_link="", source="s",
             job_type="FT", posted_date="")
    j2 = Job(title="AI Engineer", company="Acme Inc", location="R",
             description="d different", apply_link="", source="s",
             job_type="FT", posted_date="")
    assert j1.id == j2.id
    assert "/" not in j1.id and " " not in j1.id


def test_job_from_dict_fills_missing_required_fields():
    # Old-format record without job_type/posted_date must not crash.
    j = Job.from_dict({"title": "X", "company": "Y"})
    assert j.job_type == "Full Time"
    assert j.posted_date == ""


def test_job_to_dict_round_trip():
    j = Job(title="Eng", company="Acme", location="Remote", description="python",
            apply_link="http://x", source="wellfound", job_type="Internship",
            posted_date="today", salary="$100k")
    j2 = Job.from_dict(j.to_dict())
    assert j2.title == j.title
    assert j2.company == j.company
    assert j2.salary == "$100k"
    assert j2.id == j.id


# --- Application -------------------------------------------------------------

def test_application_advance_only_forward():
    a = Application(job_id="x", company="y", title="z")
    assert a.status == "discovered"
    a.advance_to("matched")
    assert a.status == "matched"
    # Should not regress.
    a.advance_to("discovered")
    assert a.status == "matched"
    # Ignores unknown statuses.
    a.advance_to("nonsense")
    assert a.status == "matched"


def test_application_status_pipeline_order():
    # Sanity check on the canonical order.
    assert STATUS_PIPELINE[0] == "discovered"
    assert STATUS_PIPELINE[-1] == "reported"
    assert STATUS_PIPELINE.index("resume_generated") < STATUS_PIPELINE.index("email_drafted")


# --- GeneratedDocument -------------------------------------------------------

def test_generated_document_round_trip():
    d = GeneratedDocument(type="resume", job_ref="abc", path="/tmp/x.txt", note="n")
    d2 = GeneratedDocument.from_dict(d.to_dict())
    assert d2.type == "resume"
    assert d2.job_ref == "abc"
    assert d2.path == "/tmp/x.txt"
    assert d2.id == d.id
