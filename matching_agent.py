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

llm = ChatGroq(
    model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"),
    temperature=0
)


# ─────────────────────────────────────────
# NODE 1: PARSE JD
# ─────────────────────────────────────────

def parse_jd_node(state: AgentState) -> AgentState:
    print("\n📄 [Node 1] Parsing Job Description...")
    jd_text = state.get("jd_text", "")
    if not jd_text:
        state["error"] = "No job description provided."
        state["workflow_stage"] = "error"
        return state
    state["workflow_stage"] = "extract_requirements"
    state["error"] = ""
    return state


# ─────────────────────────────────────────
# NODE 2: EXTRACT REQUIREMENTS
# ─────────────────────────────────────────

def extract_requirements_node(state: AgentState) -> AgentState:
    print("\n🔍 [Node 2] Extracting Requirements...")
    jd_text = state.get("jd_text", "")

    prompt = f"""Analyze this job description and extract requirements.
Return ONLY valid JSON in this exact format with no extra text:
{{
  "title": "job title here",
  "must_have": ["skill1", "skill2"],
  "nice_to_have": ["skill3", "skill4"],
  "experience_years": 3,
  "education": "Bachelor's degree"
}}

Job Description:
{jd_text}"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        requirements = json.loads(raw)
    except Exception as e:
        print(f"   ⚠️ Using default requirements: {e}")
        requirements = {
            "title": "Software Developer",
            "must_have": ["JavaScript", "React", "Node.js"],
            "nice_to_have": ["TypeScript", "MongoDB"],
            "experience_years": 0,
            "education": "B.Tech"
        }

    state["job_requirements"] = requirements
    state["workflow_stage"]   = "search_resumes"
    print(f"   ✅ Must-have skills: {requirements.get('must_have', [])}")
    return state


# ─────────────────────────────────────────
# NODE 3: SEARCH RESUMES
# ─────────────────────────────────────────

def search_resumes_node(state: AgentState) -> AgentState:
    print("\n🔎 [Node 3] Searching Resumes...")
    index_all_resumes()

    requirements = state.get("job_requirements", {})
    must_have    = requirements.get("must_have", [])
    jd_text      = state.get("jd_text", "")

    query      = jd_text if jd_text else " ".join(must_have)
    candidates = search_resumes(query, top_k=10)

    state["all_candidates"]  = candidates
    state["workflow_stage"]  = "rank_candidates"
    print(f"   ✅ Found {len(candidates)} candidates")
    return state


# ─────────────────────────────────────────
# NODE 4: RANK CANDIDATES
# ─────────────────────────────────────────

def rank_candidates_node(state: AgentState) -> AgentState:
    print("\n🏆 [Node 4] Ranking Candidates...")

    candidates   = state.get("all_candidates", [])
    requirements = state.get("job_requirements", {})
    round_num    = state.get("current_round", 1)

    if not candidates:
        state["error"]          = "No candidates found."
        state["workflow_stage"] = "generate_report"
        return state

    ranked = []
    for candidate in candidates:
        prompt = f"""Score this candidate for the job. Return ONLY valid JSON with no extra text:
{{
  "score": 85,
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1"],
  "reasoning": "Brief explanation here",
  "recommendation": "hire"
}}
recommendation must be one of: hire, maybe, no-hire

Job Requirements:
Must Have: {requirements.get('must_have', [])}
Nice to Have: {requirements.get('nice_to_have', [])}
Experience Needed: {requirements.get('experience_years', 0)} years

Candidate Resume:
{candidate['raw_text'][:1500]}"""

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            result = json.loads(raw)
        except Exception as e:
            print(f"   ⚠️ Scoring error for {candidate['name']}: {e}")
            result = {
                "score": 50,
                "strengths": ["Has relevant education"],
                "gaps": ["Could not fully evaluate"],
                "reasoning": "Automatic score assigned",
                "recommendation": "maybe"
            }

        candidate.update(result)
        ranked.append(candidate)
        print(f"   • {candidate['name']}: {result.get('score', 0)}/100")

    ranked.sort(key=lambda x: x.get("score", 0), reverse=True)

    top_n = 3 if round_num >= 2 else 10
    state["shortlisted_candidates"] = ranked[:top_n]
    state["all_candidates"]         = ranked
    state["workflow_stage"]         = "generate_report"
    return state


# ─────────────────────────────────────────
# NODE 5: GENERATE REPORT
# ─────────────────────────────────────────

def generate_report_node(state: AgentState) -> AgentState:
    print("\n📊 [Node 5] Generating Report...")

    candidates   = state.get("shortlisted_candidates", [])
    requirements = state.get("job_requirements", {})
    round_num    = state.get("current_round", 1)

    lines = []
    lines.append(f"# 🤖 Candidate Matching Report")
    lines.append(f"**Role:** {requirements.get('title', 'Unknown')}")
    lines.append(f"**Screening Round:** {round_num}")
    lines.append(f"**Total Reviewed:** {len(state.get('all_candidates', []))}")
    lines.append(f"**Shortlisted:** {len(candidates)}\n")
    lines.append("---\n")

    for i, c in enumerate(candidates, 1):
        rec   = c.get('recommendation', 'N/A').upper()
        emoji = "✅" if rec == "HIRE" else "🤔" if rec == "MAYBE" else "❌"
        lines.append(f"## {i}. {c.get('name', 'Unknown')}")
        lines.append(f"**Score:** {c.get('score', 0)}/100")
        lines.append(f"**Recommendation:** {emoji} {rec}")
        lines.append(f"\n**Reasoning:** {c.get('reasoning', '')}")

        if c.get("strengths"):
            lines.append("\n**✅ Strengths:**")
            for s in c["strengths"]:
                lines.append(f"- {s}")

        if c.get("gaps"):
            lines.append("\n**⚠️ Gaps:**")
            for g in c["gaps"]:
                lines.append(f"- {g}")

        if i <= 3:
            questions = generate_interview_questions(c, requirements)
            lines.append(f"\n{questions}")

        lines.append("\n---\n")

    report = "\n".join(lines)
    state["report"]         = report
    state["workflow_stage"] = "human_feedback"
    save_report(report, "matching_report.txt")
    print("   ✅ Report generated!")
    return state


# ─────────────────────────────────────────
# NODE 6: HUMAN FEEDBACK
# ─────────────────────────────────────────

def human_feedback_node(state: AgentState) -> AgentState:
    print("\n💬 [Node 6] Processing Feedback...")
    feedback  = state.get("human_feedback", "").lower().strip()
    round_num = state.get("current_round", 1)

    if not feedback or feedback in ["done", "finish", "end", "no"]:
        state["workflow_stage"] = "end"
        return state

    if state.get("needs_rerank"):
        state["current_round"]  = round_num + 1
        state["needs_rerank"]   = False
        state["workflow_stage"] = "rank_candidates"
        return state

    if round_num < 3:
        state["current_round"]  = round_num + 1
        state["workflow_stage"] = "rank_candidates"
    else:
        state["workflow_stage"] = "end"
    return state


# ─────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────

def route_after_feedback(state: AgentState) -> str:
    stage = state.get("workflow_stage", "end")
    if stage == "rank_candidates":
        return "rank_candidates"
    return END


# ─────────────────────────────────────────
# BUILD GRAPH
# ─────────────────────────────────────────

def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("parse_jd",             parse_jd_node)
    graph.add_node("extract_requirements", extract_requirements_node)
    graph.add_node("search_resumes",       search_resumes_node)
    graph.add_node("rank_candidates",      rank_candidates_node)
    graph.add_node("generate_report",      generate_report_node)
    graph.add_node("human_feedback",       human_feedback_node)

    graph.set_entry_point("parse_jd")

    graph.add_edge("parse_jd",             "extract_requirements")
    graph.add_edge("extract_requirements", "search_resumes")
    graph.add_edge("search_resumes",       "rank_candidates")
    graph.add_edge("rank_candidates",      "generate_report")
    graph.add_edge("generate_report",      "human_feedback")

    graph.add_conditional_edges(
        "human_feedback",
        route_after_feedback,
        {"rank_candidates": "rank_candidates", END: END}
    )

    return graph.compile()


agent = build_agent()