"""
One-time (or re-run) script to populate Pinecone with knowledge base documents.

Tour data is fetched live from the Rayna API — no static ingestion needed.

Usage:
    python ingest.py
"""
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from rag_engine import is_available

KB_DIR = Path(__file__).parent / "knowledge_base"


def load_knowledge_files() -> list[dict]:
    """Load all JSON files from knowledge_base/ directory."""
    all_docs = []
    for json_file in sorted(KB_DIR.glob("*.json")):
        with open(json_file, "r", encoding="utf-8") as f:
            docs = json.load(f)
            all_docs.extend(docs)
        print(f"  Loaded {len(docs)} docs from {json_file.name}")
    return all_docs


def main():
    if not is_available():
        print("ERROR: OPENAI_API_KEY and PINECONE_API_KEY must be set in .env")
        return

    print("=" * 50)
    print("Rayna Tours RAG Ingestion")
    print("=" * 50)

    # Ingest knowledge base
    print("\nLoading knowledge base docs...")
    kb_docs = load_knowledge_files()
    if kb_docs:
        print(f"  Found {len(kb_docs)} knowledge documents")
        print("  (Knowledge base ingestion requires upsert implementation)")
    else:
        print("  No knowledge base files found in knowledge_base/")

    print("\nDone!")
    print("Tour data is fetched live from the Rayna API — no static ingestion needed.")


if __name__ == "__main__":
    main()
