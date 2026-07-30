"""Tests for agent helpers (pure-logic, no LLM calls)."""

from app.agents.ats_scorer_agent import ATSScorerAgent
from app.agents.base_agent import BaseAgent
from app.agents.resume_agent import ResumeAgent
from app.models.job import Job


# --- ResumeAgent identity extraction ----------------------------------------

def test_extract_identity_finds_name_and_email():
    context = """
Some project bullet about RAG pipelines.
More bullet points about FastAPI.

Punna Bhargavi
Hyderabad, India|+91-9014969461|bhargavipunna5714@gmail.com |LinkedIn |GitHub
"""
    identity = ResumeAgent._extract_identity(context)
    assert "Punna Bhargavi" in identity
    assert "bhargavipunna5714@gmail.com" in identity


def test_extract_identity_returns_empty_if_no_email():
    context = "Just some random text without contact info."
    assert ResumeAgent._extract_identity(context) == ""


def test_extract_identity_handles_name_with_middle():
    context = """
Work experience line one.
Another experience line.

Mary Jane Watson
New York, NY|+1-555-0100|mary@example.com |LinkedIn
"""
    identity = ResumeAgent._extract_identity(context)
    assert "Mary Jane Watson" in identity
    assert "mary@example.com" in identity


def test_clean_latex_output_removes_markdown_fence():
    raw = """```tex
\\documentclass{article}
\\begin{document}
Hello
\\end{document}
```"""
    cleaned = ResumeAgent._clean_latex_output(raw)
    assert cleaned.startswith("\\documentclass")
    assert "```" not in cleaned


# --- BaseAgent qualified_jobs -----------------------------------------------

class _AgentUnderTest(BaseAgent):
    name = "test"


def test_qualified_jobs_caps_at_limit():
    jobs = [
        Job(title=f"T{i}", company=f"C{i}", location="R", description="d",
            apply_link="", source="s", job_type="FT", posted_date="",
            score=70 + i)
        for i in range(8)
    ]
    state = {
        "matched_jobs": [j.to_dict() for j in jobs],
        "threshold": 60.0,
        "top_matches_limit": 3,
    }
    a = _AgentUnderTest()
    qualified = a.qualified_jobs(state)
    assert len(qualified) == 3
    # Highest scores first.
    assert qualified[0].score == 77
    assert qualified[2].score == 75


def test_qualified_jobs_filters_below_threshold():
    jobs = [
        Job(title="High", company="A", location="R", description="d",
            apply_link="", source="s", job_type="FT", posted_date="", score=80),
        Job(title="Low", company="B", location="R", description="d",
            apply_link="", source="s", job_type="FT", posted_date="", score=40),
    ]
    state = {"matched_jobs": [j.to_dict() for j in jobs], "threshold": 65.0}
    a = _AgentUnderTest()
    qualified = a.qualified_jobs(state)
    assert len(qualified) == 1
    assert qualified[0].title == "High"


# --- ATSScorerAgent keyword scoring -----------------------------------------

def test_ats_keyword_score_basic():
    resume = "Python FastAPI RAG LangChain PostgreSQL AWS"
    jd = "Python FastAPI RAG LangChain Docker Kubernetes"
    score = ATSScorerAgent.keyword_score(resume, jd)
    # 4 of 6 JD keywords overlap (python, fastapi, rag, langchain).
    assert 60.0 <= score <= 70.0


def test_ats_keyword_score_no_overlap():
    score = ATSScorerAgent.keyword_score("Java Spring Hibernate", "Python FastAPI RAG")
    assert score == 0.0


def test_ats_keyword_score_empty_jd():
    assert ATSScorerAgent.keyword_score("Python", "") == 0.0
