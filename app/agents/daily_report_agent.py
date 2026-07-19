"""DailyReportAgent: produce a markdown summary of the day's run.

Reads from the matched-job, application and generated-document
repositories to build reports/report_YYYY-MM-DD.md. This is the
human-readable surface of the entire pipeline.
"""

from __future__ import annotations

from datetime import date

from app.agents.base_agent import BaseAgent
from app.repository.application_repo import ApplicationRepository
from app.repository.generated_doc_repo import GeneratedDocumentRepository
from app.repository.job_repo import MatchedJobRepository


class DailyReportAgent(BaseAgent):
    name = "daily_report"

    def __init__(self):
        super().__init__()
        self.matched_repo = MatchedJobRepository()
        self.app_repo = ApplicationRepository()
        self.docs_repo = GeneratedDocumentRepository()

    def run(self, state: dict) -> dict:
        self.log.info("=== Daily Report Agent Started ===")
        today = date.today().isoformat()
        matched = self.matched_repo.all()
        matched.sort(key=lambda j: j.score, reverse=True)
        apps = self.app_repo.all()
        summary = self.app_repo.summary()

        resumes = self.docs_repo.by_type("resume")
        cover_letters = self.docs_repo.by_type("cover_letter")
        emails = self.docs_repo.by_type("cold_email")

        lines = [
            f"# Job Agent Daily Report - {today}",
            "",
            "## Summary",
            f"- Jobs discovered: **{len(state.get('jobs', []))}**",
            f"- Jobs matched (>= threshold): **{len(matched)}**",
            f"- Resumes generated: **{len(resumes)}**",
            f"- Cover letters drafted: **{len(cover_letters)}**",
            f"- Cold emails drafted: **{len(emails)}**",
            f"- Applications tracked: **{len(apps)}**",
            "",
            "## Application Status Breakdown",
        ]
        for status, count in summary.items():
            lines.append(f"- {status}: {count}")

        lines += ["", "## Top Matches"]
        if matched:
            lines.append("| Rank | Title | Company | Score | ATS | Source |")
            lines.append("|------|-------|---------|-------|-----|--------|")
            for i, job in enumerate(matched[:15], 1):
                lines.append(
                    f"| {i} | {job.title} | {job.company} | {job.score:.1f} "
                    f"| {job.ats_score:.1f} | {job.source} |"
                )
        else:
            lines.append("_No qualified matches today._")

        lines += ["", "## Artifacts"]
        for doc_type, label in (
            ("resume", "Resumes"),
            ("cover_letter", "Cover Letters"),
            ("cold_email", "Cold Emails"),
        ):
            lines.append(f"### {label}")
            items = self.docs_repo.by_type(doc_type)
            if not items:
                lines.append("_None._")
            for d in items:
                lines.append(f"- `{d.path}`")
            lines.append("")

        content = "\n".join(lines)
        stem = f"report_{today}"
        doc = self.write_report(stem, content)
        state["report_path"] = doc.path
        self.log.info("Daily report written to %s", doc.path)
        return state
