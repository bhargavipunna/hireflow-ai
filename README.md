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
| `app/agents/` | 10 pipeline nodes: Profile, Scraper, Matcher, Resume, CoverLetter, ATSScorer, Recruiter, ColdEmail, Tracker, DailyReport. |
| `app/services/` | Stateless services: `LLMService` (Ollama with optional NVIDIA/Sarvam fallback), `EmbeddingService` (BGE), `ScoreService` (cosine). |
| `app/repository/` | JSON-file-backed persistence with atomic writes: jobs, matched jobs, applications, generated-doc index. |
| `app/scrapers/` | `BaseScraper` + 7 per-source adapters, driven by `config/sources/*.json`. `ScraperManager` runs them concurrently. |
| `app/rag/` | PDF ingest → chunk → embed → ChromaDB; semantic retriever. |
| `app/models/` | Dataclasses: `Job`, `Application`, `GeneratedDocument`. |
| `app/config/` | `settings`, `logger`, `exceptions`. |
| `app/utils/` | `http_client` (retry + rotating UA), `retry` (tenacity wrapper). |
| `app/graph/` | LangGraph `AgentState` + compiled 10-node `workflow`. |
| `app/cli/` | Subcommand CLI: `run`, `scrape`, `stats`, `report`, `serve`, `schedule`. |
| `app/api/` | FastAPI REST API for programmatic access and dashboards. |
| `app/scheduler/` | APScheduler daemon for daily automated runs. |

---

## Project structure

```
app/
  agents/        # 10 pipeline agents
  api/           # FastAPI REST endpoints
  cli/           # subcommand interface
  config/        # settings, logger, exceptions
  graph/         # LangGraph state + workflow
  models/        # Job, Application, GeneratedDocument
  rag/           # vectordb, ingest, retriever
  repository/    # base + job / application / generated-doc repos
  scheduler/     # APScheduler daemon
  scrapers/      # base + 7 per-source scrapers + manager
  services/      # llm, embedding, score
  utils/         # http_client, retry
config/
  sources/       # one JSON per source: endpoints, selectors, fallback jobs
data/            # resume, jobs, generated artifacts (gitignored)
logs/            # rotating logs (gitignored)
tests/           # pytest suite (39 tests)
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
Preferred: put your master LaTeX resume at `data/resume/resume.tex`.
The system will use that source as the template and write tailored
duplicates as `.tex` files under `data/generated_resumes/`.

Fallback: put your resume PDF at `data/resume/resume.pdf`.

You can also point at a direct `.tex` URL with `MASTER_RESUME_TEX_URL`
in `.env`; the file is downloaded into `data/resume/` before the run.
An Overleaf project page URL is not a direct `.tex` file, so export the
source into `data/resume/resume.tex` unless you have Overleaf Git access.

### Run the full pipeline
```bash
python -m app.cli.main run
```

This will:
1. Ingest your resume into ChromaDB.
2. Scrape jobs from every enabled source (with graceful fallback to sample data).
3. Score and rank jobs against your profile.
4. For the top N jobs above `MATCH_THRESHOLD`: draft a resume, cover letter, and cold email.
5. Run ATS scoring on generated resumes.
6. Update the application tracker.
7. Write a markdown report to `data/reports/report_YYYY-MM-DD.md`.

After a run, inspect applications that are ready for your approval:

```bash
python -m app.cli.main review
python -m app.cli.main approve <job_id> --notes "Looks good"
python -m app.cli.main reject <job_id> --notes "Not relevant"
```

---

## CLI commands

| Command | What it does |
|---------|-------------|
| `python -m app.cli.main run` | Full pipeline (scrape → match → generate → report). |
| `python -m app.cli.main scrape --sources wellfound,remote` | Scrape only (optional source filter). |
| `python -m app.cli.main stats` | Show repository counts and top matches. |
| `python -m app.cli.main review` | Show applications waiting for approval. |
| `python -m app.cli.main approve <job_id>` | Approve an application for a future apply step. |
| `python -m app.cli.main reject <job_id>` | Reject an application so automation skips it. |
| `python -m app.cli.main report` | Re-generate today's daily report from current state. |
| `python -m app.cli.main serve --port 8000` | Start the FastAPI server. |
| `python -m app.cli.main schedule --hour 9` | Start the daily scheduler daemon (runs pipeline at 09:00 UTC). |

---

## FastAPI endpoints

Start the server with `python -m app.cli.main serve`, then:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Liveness probe. |
| `/stats` | GET | Aggregate counts across all repositories. |
| `/jobs/matched?limit=N` | GET | Top matched jobs (default 50). |
| `/jobs/{job_id}` | GET | Single matched job by ID. |
| `/applications?status=X` | GET | Tracked applications, optionally filtered. |
| `/applications/review` | GET | Applications waiting for approval. |
| `/applications/{job_id}/approve` | POST | Approve a reviewed application. |
| `/applications/{job_id}/reject` | POST | Reject an application. |
| `/documents?doc_type=X` | GET | Generated artifacts, optionally filtered. |
| `/report/today` | GET | Today's daily report content. |
| `/actions/run` | POST | Trigger a full pipeline run (synchronous). |
| `/actions/scrape` | POST | Trigger scrapers only. |

Interactive docs at `http://127.0.0.1:8000/docs` (Swagger UI).

---

## Configuration

All settings are env-driven (see `.env.example`). Highlights:

| Var | Default | Purpose |
|-----|---------|---------|
| `LLM_PROVIDER_ORDER` | `ollama` | Comma-separated generation fallback order, e.g. `ollama,nvidia,sarvam`. |
| `LLM_RETRIES` | `2` | Attempts per LLM provider before trying the next provider. |
| `OLLAMA_MODEL` | `qwen3:8b` | LLM model tag. |
| `NVIDIA_API_KEY` | *(empty)* | Optional NVIDIA NIM API key from build.nvidia.com. |
| `NVIDIA_MODEL` | `meta/llama-3.1-8b-instruct` | NVIDIA fallback model. |
| `SARVAM_API_KEY` | *(empty)* | Optional Sarvam API key. |
| `SARVAM_MODEL` | `sarvam-105b` | Sarvam fallback model. |
| `MASTER_RESUME_TEX_PATH` | `data/resume/resume.tex` | Preferred local LaTeX resume template. |
| `MASTER_RESUME_TEX_URL` | *(empty)* | Optional direct `.tex` URL to download before a run. |
| `MATCH_THRESHOLD` | `65` | Min score (0-100) for artifact generation. |
| `TOP_MATCHES` | `10` | Max jobs that get resumes/cover-letters/emails. |
| `TOP_K` | `5` | Resume chunks retrieved per job. |
| `SCRAPER_RETRIES` | `3` | Per-URL retry attempts. |
| `SCRAPER_CONCURRENCY` | `5` | Parallel scrapers. |
| `SCRAPER_ENABLED_SOURCES` | *(all)* | Optional allow-list of source stems. |
| `SEND_EMAILS` | `false` | Reserved — Phase 1 is always draft-only. |
| `AUTO_APPLY` | `false` | Reserved — Phase 1 is always draft-only. |

### Scrapers are config-driven

Each source lives at `config/sources/<name>.json` with endpoints and
fallback jobs. The `ats` source supports public Greenhouse, Lever, Ashby,
and SmartRecruiters feeds through `boards` entries, which is usually more
reliable than scraping login-heavy aggregators. Edit `config/sources/ats.json`
to add companies that publish public ATS feeds.

---

## Running tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

39 tests covering models, repositories, scrapers, CLI, and API.

---

## Safety & ethics

- **Cold emails and applications are drafts only.** No email is sent
  and no form is submitted. Files are written under `data/emails/`.
- **Recruiter contact info is inferred**, not scraped. The
  `RecruiterAgent` derives a generic `careers@company.com` pattern.
  Treat these as guesses pending verification.
- Scrapers use a single shared session, retry with backoff, and fall
  back to sample data rather than hammering blocked endpoints.
- Applications stop at `ready_for_review` until you explicitly approve
  or reject them. There is still no final-submit automation in this phase.

---

## Tech stack

**AI:** Qwen3 8B (Ollama) with optional NVIDIA NIM / Sarvam fallback · Sentence-Transformers (BGE-small) · ChromaDB · LangGraph
**Backend:** Python · requests + BeautifulSoup + tenacity · FastAPI · APScheduler
**Storage:** JSON files via a repository layer
**Testing:** pytest (39 tests)

---

## Project status

Version: v0.3 — Phase 1 + Phase 2 complete.

### Completed
- ✅ 10-node LangGraph pipeline (profile, scraper, matcher, resume, cover letter, ATS scorer, recruiter, cold email, tracker, daily report)
- ✅ Repository layer with atomic writes
- ✅ Config-driven scrapers (7 sources) with retry + rotating UA + fallback
- ✅ Centralized logging + exception hierarchy
- ✅ Subcommand CLI (`run`, `scrape`, `stats`, `report`, `serve`, `schedule`)
- ✅ FastAPI REST API with Swagger docs
- ✅ APScheduler daily daemon
- ✅ 39 pytest tests

### Future enhancements
- Real auto-apply via Playwright (behind explicit opt-in)
- More company-specific ATS feeds and direct company career pages
- Optional SMTP email sending (behind `SEND_EMAILS=true`)
- Web dashboard frontend (React / Streamlit)
- Multi-user / multi-resume support
