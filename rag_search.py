import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
from tools import read_resume, list_resumes

load_dotenv()

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
COLLECTION_NAME = "resumes"


# ─────────────────────────────────────────
# SETUP CHROMADB
# ─────────────────────────────────────────

def get_chroma_client():
    """Get or create ChromaDB client (ephemeral for Cloud compatibility)."""
    client = chromadb.EphemeralClient()
    return client


def get_embedding_function():
    """Use default ChromaDB embeddings (no dependencies)."""
    return embedding_functions.DefaultEmbeddingFunction()


def get_collection():
    """Get or create the resumes collection."""
    client = get_chroma_client()
    ef = get_embedding_function()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef
    )
    return collection


# ─────────────────────────────────────────
# INDEX RESUMES
# ─────────────────────────────────────────

def index_all_resumes() -> str:
    """Read all resumes and store in ChromaDB."""
    collection = get_collection()
    resume_files = list_resumes()

    if not resume_files:
        return "No resume files found in data/resumes/"

    indexed = 0

    for file_path in resume_files:
        candidate_id = os.path.basename(file_path)
        text = read_resume(file_path)
        
        if text and not text.startswith("Error"):
            try:
                collection.add(
                    documents=[text],
                    ids=[candidate_id],
                    metadatas=[{
                        "file_path": file_path,
                        "filename": candidate_id
                    }]
                )
                indexed += 1
            except Exception as e:
                print(f"Error indexing {candidate_id}: {e}")

    return f"✅ Indexed {indexed} resume(s)"


def reindex_resumes() -> str:
    """Force re-index all resumes."""
    return index_all_resumes()


# ─────────────────────────────────────────
# SEARCH RESUMES
# ─────────────────────────────────────────

def search_resumes(
    query: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Search resumes using semantic similarity."""
    try:
        collection = get_collection()
        count = collection.count()
        
        if count == 0:
            index_all_resumes()
            count = collection.count()

        if count == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, count)
        )

        candidates = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                candidates.append({
                    "id": doc_id,
                    "file_path": results["metadatas"][0][i].get("file_path", ""),
                    "name": doc_id.replace(".txt", "")
                                   .replace(".pdf", "")
                                   .replace(".docx", "")
                                   .replace("_", " ")
                                   .title(),
                    "raw_text": results["documents"][0][i],
                    "similarity_score": round(1 - results["distances"][0][i], 3)
                })

        return candidates
    except Exception as e:
        print(f"Search error: {e}")
        return []


def search_by_skills(
    skills: List[str],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Search resumes by skills."""
    query = "Skills and experience in: " + ", ".join(skills)
    return search_resumes(query, top_k)