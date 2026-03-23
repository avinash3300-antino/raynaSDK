"""
RAG engine for Rayna Tours — Pinecone + OpenAI embeddings.

Uses text-embedding-ada-002 to match the existing Pinecone index.
Existing records use metadata schema:
  - title, description, content, pageType, source
  - mainImage, imageUrls, location, destination
  - itinerary, duration, price, highlights
  - chunkIndex, totalChunks, parentDocumentId
"""
from __future__ import annotations

import os
import re
from typing import Any

from openai import OpenAI
from pinecone import Pinecone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "raynatours-test1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")

# ---------------------------------------------------------------------------
# Clients (lazy-initialized singletons)
# ---------------------------------------------------------------------------

_openai_client: OpenAI | None = None
_pinecone_index = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        _pinecone_index = pc.Index(PINECONE_INDEX_NAME)
    return _pinecone_index


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------


def get_embedding(text: str) -> list[float]:
    """Get OpenAI embedding for a single text string."""
    response = _get_openai().embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


def search(
    query: str,
    top_k: int = 5,
    filter_dict: dict | None = None,
) -> list[dict[str, Any]]:
    """Embed the query and search Pinecone."""
    query_vec = get_embedding(query)
    index = _get_index()
    results = index.query(
        vector=query_vec,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )
    return [
        {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata or {},
        }
        for match in results.matches
    ]


def search_tours(query: str, top_k: int = 6) -> list[dict[str, Any]]:
    """Search only tour pages."""
    return search(query, top_k=top_k, filter_dict={"pageType": "tour"})


def search_all(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search across all document types."""
    return search(query, top_k=top_k)


# ---------------------------------------------------------------------------
# Deduplicate by parentDocumentId (keep highest-scoring chunk per tour)
# ---------------------------------------------------------------------------


def dedupe_by_parent(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only the best-scoring chunk per parent document."""
    seen: dict[str, dict[str, Any]] = {}
    for r in results:
        parent = r["metadata"].get("parentDocumentId") or r["id"]
        if parent not in seen or r["score"] > seen[parent]["score"]:
            seen[parent] = r
    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


# ---------------------------------------------------------------------------
# URL builder from title
# ---------------------------------------------------------------------------


def _build_url_from_title(title: str) -> str:
    """Build a raynatours.com URL by slugifying the tour title."""
    # Remove " | Rayna Tours" or similar suffixes
    clean = title.split(" | ")[0].strip() if " | " in title else title
    # Lowercase, replace non-alphanumeric with hyphens, collapse multiple hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if slug:
        return f"https://www.raynatours.com/{slug}"
    return "https://www.raynatours.com"


# ---------------------------------------------------------------------------
# Format RAG results into tour card format (for widget display)
# ---------------------------------------------------------------------------


def format_rag_tour_card(meta: dict[str, Any]) -> dict[str, Any]:
    """Convert Pinecone metadata into the tour card format expected by widgets."""
    title = meta.get("title", "Tour")
    # Clean title: remove " | Rayna Tours" suffix
    if " | " in title:
        title = title.split(" | ")[0].strip()

    # Extract first image from imageUrls list or use mainImage
    image = meta.get("mainImage", "")
    image_urls = meta.get("imageUrls")
    if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
        image = image_urls[0]

    # Price — use 0 as fallback (not None) to match API format exactly
    price_raw = meta.get("price", "")
    try:
        price = float(price_raw) if price_raw else 0
    except (ValueError, TypeError):
        price = 0

    duration = meta.get("duration", "") or ""
    location = meta.get("destination", "") or meta.get("location", "") or ""

    # Clean location if it looks like itinerary text
    if location.startswith("Day "):
        location = location.split("Depart")[0].replace("Day 1:", "").strip()

    url = meta.get("url", "") or meta.get("urlPath", "")
    if url and not url.startswith("http"):
        url = f"https://www.raynatours.com{url}" if url.startswith("/") else f"https://www.raynatours.com/{url}"
    if not url:
        url = _build_url_from_title(meta.get("title", ""))
    slug = url.replace("https://www.raynatours.com/", "").replace("https://www.raynatours.com", "")

    # Match exact same shape as format_tour_card() in rayna_utils.py
    return {
        "id": meta.get("parentDocumentId", ""),
        "title": title,
        "slug": slug,
        "image": image,
        "location": location,
        "category": meta.get("pageType", "tour").capitalize(),
        "originalPrice": None,
        "currentPrice": price,
        "currency": "AED",
        "discount": None,
        "discountPercentage": None,
        "isRecommended": False,
        "isNew": False,
        "rPoints": 0,
        "rating": None,
        "reviewCount": None,
        "duration": duration,
        "highlights": [],
        "url": url,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def is_available() -> bool:
    """Check if RAG engine is configured."""
    return bool(OPENAI_API_KEY and PINECONE_API_KEY)
