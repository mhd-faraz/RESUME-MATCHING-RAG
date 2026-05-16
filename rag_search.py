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
    """Get or create ChromaDB client."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client


def get_embedding_function():
    """Use sentence-transformers for embeddings (free, no API key)."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )


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
    skipped = 0

    for file_path in resume_files:
        candidate_id = os.path.basename(file_path)

        # Skip if already indexed
        existing = collection.get(ids=[candidate_id])
        if existing["ids"]:
            skipped += 1
            continue

        # Read and index
        text = read_resume(file_path)
        if text and not text.startswith("Error"):
            collection.add(
                documents=[text],
                ids=[candidate_id],
                metadatas=[{
                    "file_path": file_path,
                    "filename": candidate_id
                }]
            )
            indexed += 1

    return (
        f"Indexing complete. "
        f"Indexed: {indexed}, Skipped (already exist): {skipped}, "
        f"Total in DB: {indexed + skipped}"
    )


def reindex_resumes() -> str:
    """Force re-index all resumes (clears old data)."""
    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    return index_all_resumes()


# ─────────────────────────────────────────
# SEARCH RESUMES
# ─────────────────────────────────────────

def search_resumes(
    query: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Search resumes using semantic similarity.
    Returns top_k most relevant candidates.
    """
    collection = get_collection()

    # Make sure we have data
    count = collection.count()
    if count == 0:
        index_all_resumes()

    results = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count())
    )

    candidates = []
    if results and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            candidates.append({
                "id": doc_id,
                "file_path": results["metadatas"][0][i]["file_path"],
                "name": doc_id.replace(".txt", "")
                               .replace(".pdf", "")
                               .replace(".docx", "")
                               .replace("_", " ")
                               .title(),
                "raw_text": results["documents"][0][i],
                "similarity_score": round(
                    1 - results["distances"][0][i], 3
                )
            })

    return candidates


def search_by_skills(
    skills: List[str],
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Search resumes by a list of skills."""
    query = "Skills and experience in: " + ", ".join(skills)
    return search_resumes(query, top_k)