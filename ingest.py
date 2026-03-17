"""
One-time (or re-run) script to populate Pinecone with tour data
and knowledge base documents.

Usage:
    python ingest.py
"""
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from rayna_utils import TOUR_DATABASE
from rag_engine import upsert_tours, upsert_knowledge_docs, is_available

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

    # 1. Ingest tours
    print(f"\n[1/2] Ingesting {len(TOUR_DATABASE)} tours...")
    tour_count = upsert_tours(TOUR_DATABASE)
    print(f"  Upserted {tour_count} tour vectors")

    # 2. Ingest knowledge base
    print(f"\n[2/2] Loading knowledge base docs...")
    kb_docs = load_knowledge_files()
    if kb_docs:
        kb_count = upsert_knowledge_docs(kb_docs)
        print(f"  Upserted {kb_count} knowledge vectors")
    else:
        print("  No knowledge base files found in knowledge_base/")

    print(f"\nDone! Total vectors: {tour_count + len(kb_docs)}")
    print("You can now use the 'ask-rayna' tool in the MCP server.")


if __name__ == "__main__":
    main()
