"""Command-line interface for the Career Copilot.

Subcommands:
  run       Execute the full pipeline (scrape + match + generate + report).
  scrape    Only run the scrapers and persist raw jobs.
  stats     Show tracker / repository counts.
  review    Show applications waiting for approval.
  approve   Mark an application approved for a future apply step.
  reject    Mark an application rejected so automation skips it.
  report    Re-generate today's daily report from current repository state.
  serve     Start the FastAPI server (Phase 2).
  schedule  Start the daily scheduler daemon (Phase 2).

Usage:
  python -m app.cli.main run
  python -m app.cli.main stats
  python -m app.cli.main scrape --sources wellfound,remote
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

from app.config.logger import get_logger
from app.config.settings import (
    MATCH_THRESHOLD,
    TOP_MATCHES,
    ensure_dirs,
)

log = get_logger(__name__)


def _print_table(rows: list[dict], columns: list[tuple[str, str]]) -> None:
    """Print a simple aligned table. columns = [(key, header), ...]."""
    if not rows:
        print("  (none)")
        return
    widths = [
        max(len(header), *(len(str(r.get(key, ""))) for r in rows))
        for key, header in columns
    ]
    fmt = "  | ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*[header for _, header in columns]))
    print("  +" + "-+-".join("-" * w for w in widths) + "-+")
    for r in rows:
        cells = []
        for idx, (key, _) in enumerate(columns):
            w = widths[idx]
            cells.append(str(r.get(key, ""))[:w])
        print(fmt.format(*cells))


# --- subcommands ------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    """Run the full LangGraph pipeline."""
    from app.graph.workflow import workflow

    ensure_dirs()
    log.info("Starting Career Copilot run (threshold=%.1f)", float(MATCH_THRESHOLD))

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
        log.exception("Pipeline failed: %s", exc)
        return 1

    matched = result.get("matched_jobs", [])
    print("\n" + "=" * 60)
    print("CAREER COPILOT - RUN COMPLETE")
    print("=" * 60)
    print(f"\nJobs discovered : {len(result.get('jobs', []))}")
    print(f"Jobs matched    : {len(matched)}")
    print(f"Resumes drafted : {len(result.get('resumes', []))}")
    print(f"Cover letters   : {len(result.get('cover_letters', []))}")
    print(f"Cold emails     : {len(result.get('cold_emails', []))}")
    print(f"ATS scored      : {result.get('ats_scored', 0)}")

    print("\nTop matches:")
    _print_table(
        matched[:15],
        [("title", "Title"), ("company", "Company"),
         ("score", "Score"), ("ats_score", "ATS"), ("source", "Source")],
    )
    if result.get("report_path"):
        print(f"\nDaily report: {result['report_path']}")
    print("=" * 60)
    return 0


def cmd_scrape(args: argparse.Namespace) -> int:
    """Run only the scrapers."""
    ensure_dirs()
    if args.sources:
        os.environ["SCRAPER_ENABLED_SOURCES"] = args.sources
    # Re-import so env override takes effect.
    from app.scrapers.scraper_manager import ScraperManager

    mgr = ScraperManager()
    jobs = mgr.collect_jobs()
    print(f"\nCollected {len(jobs)} jobs.")
    by_source: dict[str, int] = {}
    for j in jobs:
        by_source[j.source] = by_source.get(j.source, 0) + 1
    for src, count in sorted(by_source.items()):
        print(f"  {src}: {count}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show counts from all repositories."""
    ensure_dirs()
    from app.repository.application_repo import ApplicationRepository
    from app.repository.generated_doc_repo import GeneratedDocumentRepository
    from app.repository.job_repo import JobRepository, MatchedJobRepository

    jr = JobRepository()
    mr = MatchedJobRepository()
    ar = ApplicationRepository()
    dr = GeneratedDocumentRepository()

    print("\n=== Repository Stats ===\n")
    print(f"Raw jobs stored      : {len(jr.all())}")
    print(f"Matched jobs stored  : {len(mr.all())}")
    print(f"Applications tracked : {len(ar.all())}")
    print(f"Generated documents  : {len(dr.all())}")
    print(f"  - resumes          : {len(dr.by_type('resume'))}")
    print(f"  - cover letters    : {len(dr.by_type('cover_letter'))}")
    print(f"  - cold emails      : {len(dr.by_type('cold_email'))}")
    print(f"  - reports          : {len(dr.by_type('report'))}")

    print("\nApplication status:")
    for status, count in ar.summary().items():
        if count:
            print(f"  {status:25s}: {count}")

    print("\nTop 10 matched jobs:")
    _print_table(
        [j.to_dict() for j in mr.top(10)],
        [("title", "Title"), ("company", "Company"),
         ("score", "Score"), ("ats_score", "ATS"), ("source", "Source")],
    )
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Show applications waiting for human approval."""
    ensure_dirs()
    from app.repository.application_repo import ApplicationRepository

    ar = ApplicationRepository()
    rows = [a.to_dict() for a in ar.review_queue()[: args.limit]]
    print("\n=== Review Queue ===\n")
    _print_table(
        rows,
        [
            ("job_id", "Job ID"),
            ("title", "Title"),
            ("company", "Company"),
            ("score", "Score"),
            ("apply_link", "Apply Link"),
        ],
    )
    return 0


def _set_application_status(args: argparse.Namespace, status: str) -> int:
    ensure_dirs()
    from app.repository.application_repo import ApplicationRepository

    ar = ApplicationRepository()
    app_record = ar.set_status(args.job_id, status, notes=args.notes or "")
    if app_record is None:
        print(f"Application not found: {args.job_id}")
        return 1
    print(f"{args.job_id} -> {app_record.status}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    """Approve an application for the future apply step."""
    return _set_application_status(args, "approved")


def cmd_reject(args: argparse.Namespace) -> int:
    """Reject an application so later automation skips it."""
    return _set_application_status(args, "rejected")


def cmd_report(args: argparse.Namespace) -> int:
    """Re-generate today's daily report from current repo state."""
    ensure_dirs()
    from app.agents.daily_report_agent import DailyReportAgent

    agent = DailyReportAgent()
    state = agent.run({})
    print(f"\nReport written to: {state.get('report_path', '(unknown)')}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Start the FastAPI server."""
    import uvicorn

    ensure_dirs()
    log.info("Starting FastAPI server on %s:%s", args.host, args.port)
    print(f"Serving Career Copilot API on http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(
        "app.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    """Start the APScheduler daily daemon."""
    from app.scheduler.daemon import run_scheduler

    run_scheduler(hour=args.hour, minute=args.minute)
    return 0


# --- parser -----------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="career-copilot",
        description="AI Career Copilot - autonomous job-search assistant.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run the full pipeline.")
    p_run.set_defaults(func=cmd_run)

    # scrape
    p_scrape = sub.add_parser("scrape", help="Run scrapers only.")
    p_scrape.add_argument(
        "--sources", default="",
        help="Comma-separated source stems to enable (default: all).",
    )
    p_scrape.set_defaults(func=cmd_scrape)

    # stats
    p_stats = sub.add_parser("stats", help="Show repository / tracker stats.")
    p_stats.set_defaults(func=cmd_stats)

    # review
    p_review = sub.add_parser("review", help="Show applications waiting for approval.")
    p_review.add_argument("--limit", type=int, default=20)
    p_review.set_defaults(func=cmd_review)

    # approve / reject
    p_approve = sub.add_parser("approve", help="Approve an application by job id.")
    p_approve.add_argument("job_id")
    p_approve.add_argument("--notes", default="")
    p_approve.set_defaults(func=cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject an application by job id.")
    p_reject.add_argument("job_id")
    p_reject.add_argument("--notes", default="")
    p_reject.set_defaults(func=cmd_reject)

    # report
    p_report = sub.add_parser("report", help="Regenerate today's daily report.")
    p_report.set_defaults(func=cmd_report)

    # serve
    p_serve = sub.add_parser("serve", help="Start the FastAPI server.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true", help="Auto-reload on code changes.")
    p_serve.add_argument("--log-level", default="info")
    p_serve.set_defaults(func=cmd_serve)

    # schedule
    p_sched = sub.add_parser("schedule", help="Start the daily scheduler daemon.")
    p_sched.add_argument("--hour", type=int, default=9, help="Run hour (24h, local). Default 9.")
    p_sched.add_argument("--minute", type=int, default=0, help="Run minute. Default 0.")
    p_sched.set_defaults(func=cmd_schedule)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
