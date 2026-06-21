from typing import TypedDict, List


class AgentState(TypedDict):

    resume_text: str

    jobs: List[dict]

    matched_jobs: List[dict]

    generated_resumes: List[str]