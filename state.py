from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel


class Candidate(BaseModel):
    id: str
    name: str
    file_path: str
    raw_text: str = ""
    score: float = 0.0
    strengths: List[str] = []
    gaps: List[str] = []
    reasoning: str = ""


class JobRequirements(BaseModel):
    title: str = ""
    must_have: List[str] = []
    nice_to_have: List[str] = []
    experience_years: int = 0
    education: str = ""
    raw_jd: str = ""


class AgentState(TypedDict):
    # Conversation
    messages: List[Dict[str, str]]
    current_query: str

    # Job Description
    jd_text: str
    job_requirements: Optional[Dict[str, Any]]

    # Candidates
    all_candidates: List[Dict[str, Any]]
    shortlisted_candidates: List[Dict[str, Any]]
    final_candidates: List[Dict[str, Any]]

    # Workflow control
    current_round: int        # 1=initial, 2=deep, 3=final
    workflow_stage: str       # which node we're in
    human_feedback: str       # feedback from user
    needs_rerank: bool        # re-rank flag

    # Output
    report: str
    error: str