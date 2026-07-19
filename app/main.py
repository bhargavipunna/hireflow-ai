"""Entry point for the AI Career Copilot.

Runs the full LangGraph pipeline and prints a concise summary table,
including links to the artifacts produced (resume, cover letter, cold
email, daily report).
"""

from __future__ import annotations

import sys

from app.config.logger import get_logger
from app.config.settings import MATCH_THRESHOLD, ensure_dirs
from app.graph.workflow import workflow

log = get_logger(__name__)


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("  (none)")
        return
    headers = ["Title", "Company", "Score", "ATS", "Source"]
    widths = [max(len(h), *(len(str(r.get(h.lower(), ""))) for r in rows)) for h in headers]
    fmt = "  | ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("  +" + "-+-".join("-" * w for w in widths) + "-+")
    for r in rows[:15]:
        print(fmt.format(
            str(r.get("title", ""))[: widths[0]],
            str(r.get("company", ""))[: widths[1]],
            f"{r.get('score', 0):.1f}",
            f"{r.get('ats_score', 0):.1f}",
            str(r.get("source", "")),
        ))


def main() -> int:
    ensure_dirs()
    log.info("Starting Career Copilot run (threshold=%.1f)", float(MATCH_THRESHOLD))

    state = {
        "resume_text": "",
        "jobs": [],
        "matched_jobs": [],
        "threshold": float(MATCH_THRESHOLD),
    }

    try:
        result = workflow.invoke(state)
    except Exception as exc:
        log.exception("Pipeline failed: %s", exc)
        return 1

    print("\n" + "=" * 60)
    print("CAREER COPILOT - RUN COMPLETE")
    print("=" * 60)

    matched = result.get("matched_jobs", [])
    print(f"\nJobs discovered : {len(result.get('jobs', []))}")
    print(f"Jobs matched    : {len(matched)}")
    print(f"Resumes drafted : {len(result.get('resumes', []))}")
    print(f"Cover letters   : {len(result.get('cover_letters', []))}")
    print(f"Cold emails     : {len(result.get('cold_emails', []))}")

    print("\nTop matches:")
    _print_table(matched)

    report_path = result.get("report_path")
    if report_path:
        print(f"\nDaily report: {report_path}")

    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
