import os
import json
from typing import Any, Dict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from state import AgentState
from tools import (
    read_resume, list_resumes, save_report,
    compare_candidates, generate_interview_questions
)
from rag_search import search_resumes, index_all_resumes

load_dotenv()

# ✅ FIXED MODEL
llm = ChatGroq(
    model=os.getenv("MODEL_NAME", "llama-3-70b-8192"),
    temperature=0
)

# ─────────────────────────────────────────
# NODE 1: PARSE JD
# ─────────────────────────────────────────

def parse_jd_node(state: AgentState) -> AgentState:
    jd_text = state.get("jd_text", "")
    if not jd_text:
        state["error"] = "No job description provided."
        state["workflow_stage"] = "error"
        return state
    state["workflow_stage"] = "extract_requirements"
    return state

# ─────────────────────────────────────────
# NODE 2: EXTRACT REQUIREMENTS
# ─────────────────────────────────────────

def extract_requirements_node(state: AgentState) -> AgentState:
    jd_text = state.get("jd_text", "")

    prompt = f"""
Return ONLY JSON:
{{
  "title": "",
  "must_have": [],
  "nice_to_have": [],
  "experience_years": 0,
  "education": ""
}}

JD:
{jd_text}
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        import re
        json_str = re.search(r"\{.*\}", raw, re.DOTALL).group()
        requirements = json.loads(json_str)

    except:
        requirements = {
            "title": "Software Developer",
            "must_have": ["Python"],
            "nice_to_have": [],
            "experience_years": 0,
            "education": "Bachelor"
        }

    state["job_requirements"] = requirements
    state["workflow_stage"] = "search_resumes"
    return state

# ─────────────────────────────────────────
# NODE 3: SEARCH RESUMES
# ─────────────────────────────────────────

def search_resumes_node(state: AgentState) -> AgentState:

    # ✅ FIXED INDEXING (important)
    if not state.get("indexed", False):
        index_all_resumes()
        state["indexed"] = True

    requirements = state.get("job_requirements", {})
    query = state.get("jd_text", "") or " ".join(requirements.get("must_have", []))

    candidates = search_resumes(query, top_k=10)

    state["all_candidates"] = candidates
    state["workflow_stage"] = "rank_candidates"
    return state

# ─────────────────────────────────────────
# NODE 4: RANK
# ─────────────────────────────────────────

def rank_candidates_node(state: AgentState) -> AgentState:

    candidates = state.get("all_candidates", [])
    requirements = state.get("job_requirements", {})

    ranked = []

    for c in candidates:
        prompt = f"""
Return JSON:
{{
 "score": 0,
 "strengths": [],
 "gaps": [],
 "reasoning": "",
 "recommendation": ""
}}

JD: {requirements}
Resume: {c['raw_text'][:1000]}
"""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()

            import re
            json_str = re.search(r"\{.*\}", raw, re.DOTALL).group()
            result = json.loads(json_str)

        except:
            result = {"score": 50, "recommendation": "maybe"}

        c.update(result)
        ranked.append(c)

    ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

    state["shortlisted_candidates"] = ranked[:5]
    state["all_candidates"] = ranked
    state["workflow_stage"] = "generate_report"
    return state

# ─────────────────────────────────────────
# NODE 5: REPORT
# ─────────────────────────────────────────

def generate_report_node(state: AgentState) -> AgentState:

    candidates = state.get("shortlisted_candidates", [])
    lines = ["# Report\n"]

    for c in candidates:
        lines.append(f"{c['name']} - {c.get('score', 0)}")

    report = "\n".join(lines)

    state["report"] = report
    state["workflow_stage"] = "end"

    save_report(report, "report.txt")
    return state

# ─────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("parse_jd", parse_jd_node)
    graph.add_node("extract_requirements", extract_requirements_node)
    graph.add_node("search_resumes", search_resumes_node)
    graph.add_node("rank_candidates", rank_candidates_node)
    graph.add_node("generate_report", generate_report_node)

    graph.set_entry_point("parse_jd")

    graph.add_edge("parse_jd", "extract_requirements")
    graph.add_edge("extract_requirements", "search_resumes")
    graph.add_edge("search_resumes", "rank_candidates")
    graph.add_edge("rank_candidates", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()

agent = build_agent()