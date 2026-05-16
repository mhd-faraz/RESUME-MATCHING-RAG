# 🤖 AI Resume Matching Agent

An intelligent resume screening and candidate matching system built with **LangGraph**, **Groq LLaMA**, and **ChromaDB**. This agent automates the hiring process by parsing job descriptions, semantically searching resumes, ranking candidates, and generating detailed match reports.

---

## 🎯 Features

- 📄 **Auto JD Parsing** — Extracts must-have vs nice-to-have skills from job descriptions
- 🔍 **Semantic Resume Search** — Uses ChromaDB + sentence-transformers for intelligent matching
- 🏆 **AI-Powered Ranking** — Scores each candidate using Groq LLaMA 3.3
- 💬 **Conversational Interface** — Ask natural language questions about candidates
- 📊 **Detailed Reports** — Strengths, gaps, scores, and hire/no-hire recommendations
- 🎤 **Interview Questions** — Auto-generates screening questions per candidate
- 🔄 **Multi-Round Screening** — Initial screen → deep analysis → final recommendation

---

## 🏗️ Agent Architecture (LangGraph)

```
START
  ↓
📄 Parse JD Node
  ↓
🔍 Extract Requirements Node  (LLM — must-have vs nice-to-have)
  ↓
🔎 Search Resumes Node        (RAG — ChromaDB semantic search)
  ↓
🏆 Rank Candidates Node       (LLM — score each candidate 0-100)
  ↓
📊 Generate Report Node       (strengths, gaps, interview questions)
  ↓
💬 Human Feedback Node        (re-rank or end)
  ↓
END
```

---

## 🗂️ Project Structure

```
resume_matching_agent/
├── data/
│   ├── resumes/              ← Upload PDF/TXT/DOCX resumes here
│   └── job_descriptions/     ← Upload JD files here
├── outputs/                  ← Generated reports saved here
├── tests/                    ← Test conversation flows
├── matching_agent.py         ← Main LangGraph agent (6 nodes)
├── tools.py                  ← File tools + agent tools
├── rag_search.py             ← ChromaDB vector search
├── state.py                  ← AgentState definition
├── app.py                    ← Streamlit chat interface
├── requirements.txt
└── .env
```

---

## ⚙️ Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph |
| LLM | Groq LLaMA 3.3 70B |
| Vector Database | ChromaDB |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Frontend | Streamlit |
| File Parsing | PyPDF2, python-docx |

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/resume_matching_agent.git
cd resume_matching_agent
```

### 2. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Configure environment
Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
EMBEDDING_MODEL=all-MiniLM-L6-v2
RESUME_DIR=data/resumes
JD_DIR=data/job_descriptions
OUTPUT_DIR=outputs
CHROMA_DB_PATH=./chroma_db
```

> Get your free Groq API key at [console.groq.com](https://console.groq.com)

### 4. Run the app
```bash
streamlit run app.py
```

---

## 💬 How to Use

1. **Upload Resumes** — Add PDF/TXT/DOCX resumes in the sidebar
2. **Upload JD** — Upload or paste the job description
3. **Run Full Match** — Click 🚀 to start the agent pipeline
4. **Chat** — Ask natural language questions:

```
Who is the best candidate?
Why did Anubhav rank higher than Faraz?
Compare top 3 candidates side by side
What are the gaps for each candidate?
Generate interview questions for the top candidate
Who should we hire?
Show me the full report
```

---

## 🧪 Test Scenarios

| # | Query | Expected Response |
|---|-------|------------------|
| 1 | "Who is the best candidate?" | Top ranked candidate with score & reasoning |
| 2 | "Why did Anubhav rank higher?" | Detailed comparison explanation |
| 3 | "Compare top 3 candidates" | Side-by-side comparison table |
| 4 | "What are the gaps?" | Skill gaps for each candidate |
| 5 | "Generate interview questions" | Tailored screening questions |

---

## 📊 Agent State

```python
class AgentState(TypedDict):
    messages: List[Dict]           # Conversation history
    jd_text: str                   # Job description
    job_requirements: Dict         # Parsed must-have/nice-to-have
    all_candidates: List[Dict]     # All searched candidates
    shortlisted_candidates: List   # Ranked shortlist
    current_round: int             # Screening round (1/2/3)
    workflow_stage: str            # Current node
    human_feedback: str            # User feedback
    report: str                    # Generated report
```

---

## 🛠️ Tools Available to Agent

| Tool | Description |
|------|-------------|
| `read_resume()` | Auto-detect and read PDF/DOCX/TXT |
| `list_resumes()` | List all resume files |
| `search_resumes()` | Semantic search via ChromaDB |
| `extract_requirements()` | Parse JD into structured requirements |
| `compare_candidates()` | Side-by-side comparison table |
| `generate_interview_questions()` | Create screening questions |
| `save_report()` | Save final report to outputs/ |

---

## 👥 Sample Results

```
🤖 Candidate Matching Report
Role: Full Stack Developer | Round: 1 | Total: 5

1. Anubhav Sharma     — 90/100  ✅ HIRE
2. Faiz ur Rahman     — 90/100  ✅ HIRE
3. Zeeshan Mirza      — 90/100  🤔 MAYBE
4. Asad Khan          — 80/100  🤔 MAYBE
5. Faraz Ahmad        — 60/100  🤔 MAYBE
```

---

## 📝 License

MIT License — feel free to use and modify.

---

## 🙋 Author

**Mohammad Faraz**
- GitHub: [@mohammadfaraz](https://github.com/mohammadfaraz)
- Email: siddiquifaraz122001@gmail.com