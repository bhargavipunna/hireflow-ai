from langgraph.graph import (
    StateGraph,
    END
)

from app.graph.state import (
    AgentState
)

from app.agents.profile_agent import (
    ProfileAgent
)

from app.agents.scraper_agent import (
    ScraperAgent
)

from app.agents.matcher_agent import (
    MatcherAgent
)
from app.agents.resume_agent import (
    ResumeAgent
)

profile_agent = ProfileAgent()

scraper_agent = ScraperAgent()

matcher_agent = MatcherAgent()

resume_agent = ResumeAgent()

builder = StateGraph(
    AgentState
)


builder.add_node(
    "profile_agent",
    profile_agent.run
)

builder.add_node(
    "scraper_agent",
    scraper_agent.run
)

builder.add_node(
    "matcher_agent",
    matcher_agent.run
)


builder.set_entry_point(
    "profile_agent"
)

builder.add_node(
    "resume_agent",
    resume_agent.run
)

builder.add_edge(
    "profile_agent",
    "scraper_agent"
)

builder.add_edge(
    "scraper_agent",
    "matcher_agent"
)
builder.add_edge(
    "matcher_agent",
    "resume_agent"
)

builder.add_edge(
    "resume_agent",
    END
)



workflow = builder.compile()
print("Workflow initialized")