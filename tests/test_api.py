"""Tests for the FastAPI application.

Uses FastAPI's TestClient - no real HTTP server is started.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "career-copilot"


def test_stats_shape(client):
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    for key in ("raw_jobs", "matched_jobs", "applications",
                "generated_docs", "by_type", "application_status"):
        assert key in body
    assert set(body["by_type"]) == {"resume", "cover_letter", "cold_email", "report"}


def test_list_matched_limit(client):
    r = client.get("/jobs/matched?limit=2")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) <= 2


def test_list_matched_limit_validation(client):
    # limit=0 should fail validation (ge=1).
    r = client.get("/jobs/matched?limit=0")
    assert r.status_code == 422


def test_get_job_404(client):
    r = client.get("/jobs/does_not_exist")
    assert r.status_code == 404


def test_applications_endpoint(client):
    r = client.get("/applications")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_applications_filter(client):
    r = client.get("/applications?status=matched")
    assert r.status_code == 200
    for app in r.json():
        assert app["status"] == "matched"


def test_review_queue_endpoint(client):
    r = client.get("/applications/review")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_approve_missing_application_404(client):
    r = client.post("/applications/does_not_exist/approve", json={"notes": "ok"})
    assert r.status_code == 404


def test_reject_missing_application_404(client):
    r = client.post("/applications/does_not_exist/reject", json={"notes": "no"})
    assert r.status_code == 404


def test_documents_endpoint(client):
    r = client.get("/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_documents_filter(client):
    r = client.get("/documents?doc_type=resume")
    assert r.status_code == 200
    for doc in r.json():
        assert doc["type"] == "resume"


def test_today_report_404_if_missing(client):
    # If a report exists for today this returns 200; otherwise 404.
    # Just verify the endpoint doesn't 500.
    r = client.get("/report/today")
    assert r.status_code in (200, 404)
