import os
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import PyPDF2
from docx import Document

load_dotenv()

RESUME_DIR = os.getenv("RESUME_DIR", "data/resumes")
JD_DIR = os.getenv("JD_DIR", "data/job_descriptions")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")


# ─────────────────────────────────────────
# FILE SYSTEM TOOLS
# ─────────────────────────────────────────

def read_text_file(file_path: str) -> str:
    """Read a plain text file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def read_pdf_file(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"


def read_docx_file(file_path: str) -> str:
    """Extract text from a Word document."""
    try:
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"


def read_resume(file_path: str) -> str:
    """Auto-detect file type and read resume."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return read_pdf_file(file_path)
    elif ext == ".docx":
        return read_docx_file(file_path)
    else:
        return read_text_file(file_path)


def list_resumes() -> List[str]:
    """List all resume files in the resumes directory."""
    supported = {".pdf", ".docx", ".txt"}
    files = []
    for f in Path(RESUME_DIR).iterdir():
        if f.suffix.lower() in supported:
            files.append(str(f))
    return files


def list_job_descriptions() -> List[str]:
    """List all JD files."""
    supported = {".pdf", ".docx", ".txt"}
    files = []
    for f in Path(JD_DIR).iterdir():
        if f.suffix.lower() in supported:
            files.append(str(f))
    return files


def save_report(report: str, filename: str = "matching_report.md") -> str:
    """Save the final report to outputs folder."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return f"Report saved to {path}"


# ─────────────────────────────────────────
# AGENT TOOLS
# ─────────────────────────────────────────

def extract_requirements(jd: str) -> Dict[str, Any]:
    """
    Parse a job description into must-have
    and nice-to-have requirements.
    (LLM call happens inside the agent node.)
    """
    return {
        "raw_jd": jd,
        "status": "pending_llm_extraction"
    }


def compare_candidates(
    candidates: List[Dict[str, Any]]
) -> str:
    """Build a side-by-side comparison table."""
    if not candidates:
        return "No candidates to compare."

    lines = ["## Side-by-Side Candidate Comparison\n"]
    lines.append(f"{'Name':<20} {'Score':<8} {'Strengths':<40} {'Gaps'}")
    lines.append("-" * 90)

    for c in candidates:
        name = c.get("name", "Unknown")[:20]
        score = f"{c.get('score', 0):.1f}"
        strengths = ", ".join(c.get("strengths", []))[:40]
        gaps = ", ".join(c.get("gaps", []))[:30]
        lines.append(f"{name:<20} {score:<8} {strengths:<40} {gaps}")

    return "\n".join(lines)


def generate_interview_questions(
    candidate: Dict[str, Any],
    job_requirements: Dict[str, Any]
) -> str:
    """Generate screening questions for a candidate."""
    name = candidate.get("name", "Candidate")
    gaps = candidate.get("gaps", [])
    must_have = job_requirements.get("must_have", [])

    questions = [f"## Interview Questions for {name}\n"]
    questions.append("### Technical Questions:")
    for skill in must_have[:3]:
        questions.append(f"- Can you describe your experience with {skill}?")

    if gaps:
        questions.append("\n### Gap-Bridging Questions:")
        for gap in gaps[:3]:
            questions.append(
                f"- You appear to have limited experience with "
                f"{gap}. How would you approach learning it?"
            )

    questions.append("\n### General Questions:")
    questions.append("- Describe your most complex project.")
    questions.append("- How do you handle tight deadlines?")

    return "\n".join(questions)