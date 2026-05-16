import streamlit as st
import os
from dotenv import load_dotenv
from matching_agent import agent
from tools import compare_candidates, list_resumes, list_job_descriptions, generate_interview_questions
from rag_search import index_all_resumes, search_resumes

load_dotenv()

st.set_page_config(page_title="Resume Matching Agent", page_icon="🤖", layout="wide")
st.title("🤖 AI Resume Matching Agent")
st.caption("Powered by LangGraph + Groq Llama")

# ── SESSION STATE ──
for key, val in {
    "messages": [],
    "agent_state": None,
    "report": "",
    "jd_text": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── SIDEBAR ──
with st.sidebar:
    st.header("⚙️ Setup")

    st.subheader("📁 Upload Resumes")
    uploaded_resumes = st.file_uploader("Upload resume files", type=["pdf", "txt", "docx"], accept_multiple_files=True)
    if uploaded_resumes:
        os.makedirs("data/resumes", exist_ok=True)
        for f in uploaded_resumes:
            with open(f"data/resumes/{f.name}", "wb") as out:
                out.write(f.read())
        st.success(f"✅ {len(uploaded_resumes)} resume(s) uploaded!")
        if st.button("🔄 Index Resumes"):
            with st.spinner("Indexing..."):
                result = index_all_resumes()
            st.success(result)

    st.divider()

    st.subheader("📋 Upload Job Description")
    uploaded_jd = st.file_uploader("Upload JD file", type=["pdf", "txt", "docx"])
    if uploaded_jd:
        os.makedirs("data/job_descriptions", exist_ok=True)
        jd_bytes = uploaded_jd.read()
        with open(f"data/job_descriptions/{uploaded_jd.name}", "wb") as out:
            out.write(jd_bytes)
        st.session_state.jd_text = jd_bytes.decode("utf-8", errors="ignore")
        st.success("✅ JD uploaded!")

    st.divider()
    st.subheader("📊 Status")
    st.metric("Resumes Found", len(list_resumes()))
    st.metric("Job Descriptions Found", len(list_job_descriptions()))
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.session_state.agent_state = None
        st.session_state.report = ""
        st.rerun()

# ── JD TEXT AREA ──
st.subheader("📋 Job Description")
jd_input = st.text_area(
    "Paste your Job Description here (or upload in sidebar):",
    value=st.session_state.jd_text,
    height=150,
    placeholder="We are looking for a Full Stack Developer..."
)
if jd_input:
    st.session_state.jd_text = jd_input

# ── QUICK ACTIONS ──
st.subheader("⚡ Quick Actions")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🚀 Run Full Match"):
        if not st.session_state.jd_text:
            st.error("❌ Please enter a Job Description first!")
        else:
            st.session_state.messages.append({"role": "user", "content": "Run full candidate matching"})
            with st.spinner("🤖 Agent working... please wait 30-60 seconds"):
                try:
                    result = agent.invoke({
                        "jd_text": st.session_state.jd_text,
                        "messages": [],
                        "current_query": "Run full matching",
                        "all_candidates": [],
                        "shortlisted_candidates": [],
                        "final_candidates": [],
                        "current_round": 1,
                        "workflow_stage": "parse_jd",
                        "human_feedback": "done",
                        "needs_rerank": False,
                        "report": "",
                        "error": "",
                        "job_requirements": None
                    })
                    st.session_state.agent_state = result
                    st.session_state.report = result.get("report", "")
                    st.session_state.messages.append({"role": "assistant", "content": "✅ Matching complete! Report generated below."})
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            st.rerun()

with col2:
    if st.button("🔍 Search Candidates"):
        if st.session_state.jd_text:
            with st.spinner("Searching..."):
                results = search_resumes(st.session_state.jd_text, top_k=5)
            names = [r["name"] for r in results] if results else []
            msg = f"🔍 Top candidates: **{', '.join(names)}**" if names else "No candidates found."
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.rerun()

with col3:
    if st.button("📊 Compare Top 3"):
        if st.session_state.agent_state:
            top3 = st.session_state.agent_state.get("shortlisted_candidates", [])[:3]
            if top3:
                comparison = compare_candidates(top3)
                st.session_state.messages.append({"role": "assistant", "content": f"```\n{comparison}\n```"})
            else:
                st.session_state.messages.append({"role": "assistant", "content": "No candidates yet. Run Full Match first."})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "Please run Full Match first."})
        st.rerun()

with col4:
    if st.button("🔄 Re-Index"):
        with st.spinner("Re-indexing..."):
            result = index_all_resumes()
        st.success(result)

# ── CHAT ──
st.divider()
st.subheader("💬 Chat with Agent")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask: 'Who is best candidate?' or 'Why did Anubhav rank higher?'"):

    st.session_state.messages.append({"role": "user", "content": prompt})
    p = prompt.lower()
    reply = ""

    if any(w in p for w in ["best", "top", "winner", "highest", "first"]):
        if st.session_state.agent_state:
            candidates = st.session_state.agent_state.get("shortlisted_candidates", [])
            if candidates:
                top = candidates[0]
                reply = (
                    f"🏆 **Best Candidate: {top['name']}**\n\n"
                    f"**Score:** {top.get('score', 0)}/100\n\n"
                    f"**Recommendation:** {top.get('recommendation','N/A').upper()}\n\n"
                    f"**Why:** {top.get('reasoning', 'N/A')}\n\n"
                    f"**Strengths:** {', '.join(top.get('strengths', []))}"
                )
            else:
                reply = "No candidates ranked yet. Please click **🚀 Run Full Match** first."
        else:
            reply = "Please click **🚀 Run Full Match** button first."

    elif any(w in p for w in ["why", "reason", "rank", "explain", "how"]):
        if st.session_state.agent_state:
            candidates = st.session_state.agent_state.get("shortlisted_candidates", [])
            if candidates:
                lines = ["📊 **Ranking Explanation:**\n"]
                for i, c in enumerate(candidates[:5], 1):
                    lines.append(f"**{i}. {c['name']}** — Score: {c.get('score',0)}/100\n{c.get('reasoning','N/A')}\n")
                reply = "\n".join(lines)
            else:
                reply = "No candidates ranked yet. Run Full Match first."
        else:
            reply = "Please click **🚀 Run Full Match** button first."

    elif "compare" in p:
        if st.session_state.agent_state:
            top3 = st.session_state.agent_state.get("shortlisted_candidates", [])[:3]
            reply = compare_candidates(top3) if top3 else "No candidates yet."
        else:
            reply = "Please run Full Match first."

    elif any(w in p for w in ["interview", "question", "ask"]):
        if st.session_state.agent_state:
            candidates = st.session_state.agent_state.get("shortlisted_candidates", [])
            requirements = st.session_state.agent_state.get("job_requirements", {})
            if candidates:
                reply = generate_interview_questions(candidates[0], requirements)
            else:
                reply = "No candidates yet. Run Full Match first."
        else:
            reply = "Please run Full Match first."

    elif any(w in p for w in ["report", "show", "result", "summary"]):
        reply = st.session_state.report if st.session_state.report else "No report yet. Run Full Match first."

    elif any(w in p for w in ["score", "mark", "point", "rating"]):
        if st.session_state.agent_state:
            candidates = st.session_state.agent_state.get("shortlisted_candidates", [])
            if candidates:
                lines = ["📊 **All Candidate Scores:**\n"]
                for i, c in enumerate(candidates, 1):
                    emoji = "✅" if c.get("recommendation") == "hire" else "🤔"
                    lines.append(f"{emoji} **{i}. {c['name']}** — {c.get('score', 0)}/100")
                reply = "\n".join(lines)
            else:
                reply = "No candidates scored yet."
        else:
            reply = "Please run Full Match first."

    elif any(w in p for w in ["find", "search", "react", "python", "developer"]):
        results = search_resumes(prompt, top_k=5)
        if results:
            names = [r["name"] for r in results]
            reply = f"🔍 **Candidates found:** {', '.join(names)}"
        else:
            reply = "No candidates found. Please index resumes first."

    else:
        reply = (
            "I can answer these questions:\n\n"
            "- 🏆 **'Who is the best candidate?'**\n"
            "- ❓ **'Why did Anubhav rank higher?'**\n"
            "- 📊 **'Compare top 3 candidates'**\n"
            "- 🎤 **'Generate interview questions'**\n"
            "- 📄 **'Show me the report'**\n"
            "- 🔢 **'Show all scores'**\n"
            "- 🔍 **'Find React developers'**"
        )

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# ── REPORT ──
if st.session_state.report:
    st.divider()
    st.subheader("📄 Matching Report")
    st.markdown(st.session_state.report)
    st.download_button(
        label="⬇️ Download Report",
        data=st.session_state.report,
        file_name="matching_report.txt",
        mime="text/plain"
    )
