"""LangGraph workflow: the end-to-end Career Copilot pipeline.

    Profile -> Scraper -> Matcher -> Resume -> CoverLetter -> ATSScorer
           -> Recruiter -> ColdEmail -> Tracker -> DailyReport -> END

Each downstream agent filters by the configured match threshold, so
low-score jobs are processed cheaply and never produce artifacts.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.ats_scorer_agent import ATSScorerAgent
from app.agents.cover_letter_agent import CoverLetterAgent
from app.agents.cold_email_agent import ColdEmailAgent
from app.agents.daily_report_agent import DailyReportAgent
from app.agents.matcher_agent import MatcherAgent
from app.agents.profile_agent import ProfileAgent
from app.agents.recruiter_agent import RecruiterAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.scraper_agent import ScraperAgent
from app.agents.tracker_agent import TrackerAgent
from app.config.logger import get_logger
from app.graph.state import AgentState

log = get_logger(__name__)

# Instantiate agents once; each node calls `.run(state)`.
profile_agent = ProfileAgent()
scraper_agent = ScraperAgent()
matcher_agent = MatcherAgent()
resume_agent = ResumeAgent()
cover_letter_agent = CoverLetterAgent()
ats_scorer_agent = ATSScorerAgent()
recruiter_agent = RecruiterAgent()
cold_email_agent = ColdEmailAgent()
tracker_agent = TrackerAgent()
daily_report_agent = DailyReportAgent()

builder = StateGraph(AgentState)

builder.add_node("profile_agent", profile_agent.run)
builder.add_node("scraper_agent", scraper_agent.run)
builder.add_node("matcher_agent", matcher_agent.run)
builder.add_node("resume_agent", resume_agent.run)
builder.add_node("cover_letter_agent", cover_letter_agent.run)
builder.add_node("ats_scorer_agent", ats_scorer_agent.run)
builder.add_node("recruiter_agent", recruiter_agent.run)
builder.add_node("cold_email_agent", cold_email_agent.run)
builder.add_node("tracker_agent", tracker_agent.run)
builder.add_node("daily_report_agent", daily_report_agent.run)

builder.set_entry_point("profile_agent")

builder.add_edge("profile_agent", "scraper_agent")
builder.add_edge("scraper_agent", "matcher_agent")
builder.add_edge("matcher_agent", "resume_agent")
builder.add_edge("resume_agent", "cover_letter_agent")
builder.add_edge("cover_letter_agent", "ats_scorer_agent")
builder.add_edge("ats_scorer_agent", "recruiter_agent")
builder.add_edge("recruiter_agent", "cold_email_agent")
builder.add_edge("cold_email_agent", "tracker_agent")
builder.add_edge("tracker_agent", "daily_report_agent")
builder.add_edge("daily_report_agent", END)

workflow = builder.compile()
log.info("Workflow initialized (10-node pipeline)")
