# AI Career Copilot

An autonomous, agentic AI system that acts as a personalized job-search
assistant. It understands your profile via a RAG knowledge base built
from your resume, scrapes jobs from multiple boards and company pages,
semantically matches each job to your profile, then drafts an
ATS-optimized resume, a tailored cover letter, a cold-email draft, and
maintains an application tracker — finally producing a daily report.

Built primarily with free / open-source tools (Ollama + Qwen3,
Sentence-Transformers, ChromaDB, LangGraph).

---

## Architecture

```
Profile ──▶ Scraper ──▶ Matcher ──▶ Resume ──▶ CoverLetter ──▶ ATSScorer
   │           │           │           │            │              │
   │           │           │           │            │              ▼
   ▼           ▼           ▼           ▼            ▼         Recruiter
 RAG ingest   jobs     matched_jobs  resumes    cover_letters      │
                                                                   ▼
                                                              ColdEmail
                                                                   │
                                                                   ▼
                                                               Tracker ──▶ DailyReport
```

### Layers

| Layer | Responsibility |
|-------|----------------|
| `app/agents/` | One class per pipeline node (Profile, Scraper, Matcher, Resume, CoverLetter, ATSScorer, Recruiter, ColdEmail, Tracker, DailyReport). |
| `app/services/` | Stateless services: `LLMService` (Ollama), `EmbeddingService` (BGE), `ScoreService` (cosine). |
| `app/repository/` | JSON-file-backed persistence with atomic writes: jobs, matched jobs, applications, generated-doc index. |
| `app/scrapers/` | `BaseScraper` + per-source adapters, driven by `config/sources/*.json`. `ScraperManager` runs them concurrently. |
| `app/rag/` | PDF ingest → chunk → embed → ChromaDB; semantic retriever. |
| `app/models/` | Dataclasses: `Job`, `Application`, `GeneratedDocument`. |
| `app/config/` | `settings`, `logger`, `exceptions`. |
| `app/utils/` | `http_client` (retry + rotating UA), `retry` (tenacity wrapper). |
| `app/graph/` | LangGraph `AgentState` + compiled `workflow`. |

---

## Project structure

```
app/
  agents/        # 10 pipeline agents
  config/        # settings, logger, exceptions
  graph/         # LangGraph state + workflow
  models/        # Job, Application, GeneratedDocument
  rag/           # vectordb, ingest, retriever
  repository/    # base + job / application / generated-doc repos
  scrapers/      # base + 7 per-source scrapers + manager
  services/      # llm, embedding, score
  utils/         # http_client, retry
config/
  sources/       # one JSON per source: endpoints, selectors, fallback jobs
data/            # resume, jobs, generated artifacts (gitignored)
logs/            # rotating logs (gitignored)
```

---

## Getting started

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) running locally with a model pulled:
  ```bash
  ollama pull qwen3:8b
  ```

### Install
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Place your resume
Put your resume PDF at `data/resume/resume.pdf`.

### Run
```bash
python -m app.main
```

The pipeline will:
1. Ingest your resume into ChromaDB.
2. Scrape jobs from every enabled source (with graceful fallback).
3. Score and rank jobs against your profile.
4. For jobs above `MATCH_THRESHOLD`: draft a resume, cover letter, and
   cold email.
5. Update the application tracker.
6. Write a markdown report to `data/reports/report_YYYY-MM-DD.md`.

---

## Configuration

All settings are env-driven (see `.env.example`). Highlights:

| Var | Default | Purpose |
|-----|---------|---------|
| `OLLAMA_MODEL` | `qwen3:8b` | LLM model tag. |
| `MATCH_THRESHOLD` | `65` | Min score (0-100) for artifact generation. |
| `TOP_K` | `5` | Resume chunks retrieved per job. |
| `SCRAPER_RETRIES` | `3` | Per-URL retry attempts. |
| `SCRAPER_CONCURRENCY` | `5` | Parallel scrapers. |
| `SCRAPER_ENABLED_SOURCES` | *(all)* | Optional allow-list of source stems. |
| `SEND_EMAILS` | `false` | Reserved — Phase 1 is always draft-only. |
| `AUTO_APPLY` | `false` | Reserved — Phase 1 is always draft-only. |

### Scrapers are config-driven

Each source lives at `config/sources/<name>.json` with `endpoints`,
CSS `selectors`, and `fallback_jobs`. Edit or add a file (e.g.
`local.json`) to point at new boards — no code change required. New
sources get the generic `CompanyScraper` automatically.

---

## Safety & ethics

- **Cold emails and applications are drafts only.** No email is sent
  and no form is submitted. Files are written under `data/emails/`.
- **Recruiter contact info is inferred**, not scraped. The
  `RecruiterAgent` derives a generic `careers@company.com` pattern.
  Treat these as guesses pending verification.
- Scrapers respect `robots.txt` spirit: they use a single shared
  session, retry with backoff, and fall back to sample data rather than
  hammering a blocked endpoint.

---

## Tech stack

**AI:** Qwen3 8B (Ollama) · Sentence-Transformers (BGE-small) · ChromaDB · LangGraph
**Backend:** Python · requests + BeautifulSoup + tenacity
**Storage:** JSON files via a repository layer

---

## Roadmap

**Phase 1 (current):** full agent set, repository layer, logging, error
handling, retry, config-driven scrapers, daily report. ✅

**Phase 2 (next):**
- APScheduler daily daemon + CLI (`run`, `report`, `stats`).
- FastAPI REST API + lightweight dashboard.
- Real auto-apply via Playwright (behind explicit opt-in).
- Deeper per-site live parsing (beyond JSON-LD + selector fallback).
- Optional SMTP email sending (behind `SEND_EMAILS=true`).

---

## Project status

Active development. Version: v0.2 (Phase 1).
