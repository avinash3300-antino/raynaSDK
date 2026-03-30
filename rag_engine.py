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
    """Build a Rayna Tours search URL from the tour title.

    Direct product URLs require real product IDs (like ``-e-18``), so we
    link to a search instead of generating broken 404 links.
    """
    if not title or title.lower() in ("tour", "no title"):
        return "https://www.raynatours.com"
    # Clean the title for a search query
    clean = re.sub(r"\s*\|.*$", "", title).strip()  # Remove " | subtitle"
    clean = re.sub(r"\s+\d{4}\s*$", "", clean).strip()  # Remove trailing year
    from urllib.parse import quote
    return f"https://www.raynatours.com/?s={quote(clean)}"


# ---------------------------------------------------------------------------
# Format RAG results into tour card format (for widget display)
# ---------------------------------------------------------------------------


def is_product_page(meta: dict[str, Any]) -> bool:
    """Return True if the RAG result looks like an actual bookable product, not a blog/article."""
    page_type = (meta.get("pageType") or "").lower()
    if page_type in ("blog", "article", "page", "category"):
        return False
    title = (meta.get("title") or "").strip().lower()
    # Skip entries with no real title
    if not title or title in ("no title", "tour", ""):
        return False
    # Blog-style titles: "The Best ...", "Top 10 ...", "X Things ...", "Guide to ..."
    blog_patterns = [
        "best ", "top ", "guide to ", "things to ", "how to ", "why ",
        "tips for ", "complete guide", "ultimate guide", "must visit",
        "places to ", "what to ",
    ]
    for pattern in blog_patterns:
        if title.startswith(pattern) or title.startswith("the " + pattern):
            return False
    return True


def format_rag_tour_card(meta: dict[str, Any]) -> dict[str, Any]:
    """Convert Pinecone metadata into the tour card format expected by widgets."""
    title = meta.get("title", "Tour")
    # Clean title: remove " | subtitle" suffix (e.g. "Tour Name | Rayna Tours")
    if " | " in title:
        title = title.split(" | ")[0].strip()
    # Clean " : subtitle" (e.g. "Dubai City Tour 2026 : Half Day Sightseeing Tour")
    if " : " in title:
        title = title.split(" : ")[0].strip()
    # Remove trailing year patterns like "2025", "2026"
    title = re.sub(r"\s+\d{4}\s*$", "", title).strip()
    # Final fallback
    if not title or title.lower() in ("no title", ""):
        title = meta.get("description", "Tour")[:60]

    # Extract first image from imageUrls list or use mainImage
    image = meta.get("mainImage", "")
    image_urls = meta.get("imageUrls")
    if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
        image = image_urls[0]

    # Price — use None for missing/zero so the widget shows "Check price" correctly
    price_raw = meta.get("price", "")
    try:
        price = float(price_raw) if price_raw else None
        if price is not None and price <= 0:
            price = None
    except (ValueError, TypeError):
        price = None

    duration = meta.get("duration", "") or ""
    location = meta.get("destination", "") or meta.get("location", "") or ""

    # Clean location if it looks like itinerary text
    if location.startswith("Day "):
        location = location.split("Depart")[0].replace("Day 1:", "").strip()

    # Extract URL — filter out namespace names like "rayna_advanced" that aren't real URLs
    def _looks_like_url(v: str) -> bool:
        """Return True if value looks like a URL or path, not a namespace/source name."""
        if not v:
            return False
        if v.startswith("http://") or v.startswith("https://"):
            return True
        if v.startswith("/"):
            return True
        # Must contain a slash to look like a path (reject "rayna_advanced", "rayna_website_advanced")
        if "/" in v and not v.startswith("rayna"):
            return True
        return False

    url = ""
    for field in ("url", "urlPath"):
        candidate = meta.get(field, "") or ""
        if _looks_like_url(candidate):
            url = candidate
            break

    # Use source URL — accept product pages (2+ path segments) and category pages
    if not url:
        source = meta.get("source", "")
        if source and _looks_like_url(source):
            path = source.replace("https://www.raynatours.com", "").strip("/")
            # Accept any raynatours.com path with at least one segment
            if path and "/" in path:
                url = source
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
