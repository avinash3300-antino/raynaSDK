"""
Rayna Tours MCP Server — ChatGPT App SDK with React UI Widgets.

Endpoints:
    /mcp     — Streamable HTTP (MCP protocol)
    /health  — Health check
    /info    — Server info
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import os

import aiohttp
import mcp.types as types
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import re

from rayna_utils import (
    RaynaApiClient,
    format_tour_card,
    format_enriched_tour_card,
    format_enriched_tour_detail,
    _is_transfers_only,
    detect_city_from_tour_name,
    CATEGORY_KEYWORDS,
)

# ---------------------------------------------------------------------------
# Load React bundles
# ---------------------------------------------------------------------------

WEB_DIR = Path(__file__).parent / "web"

try:
    TOUR_LIST_BUNDLE = (WEB_DIR / "dist/tour-list.js").read_text(encoding="utf-8")
    TOUR_DETAIL_BUNDLE = (WEB_DIR / "dist/tour-detail.js").read_text(encoding="utf-8")
    TOUR_COMPARE_BUNDLE = (WEB_DIR / "dist/tour-compare.js").read_text(encoding="utf-8")
    HAS_UI = True
except FileNotFoundError:
    print("\u26a0\ufe0f  React bundles not found. Run: cd web && npm install && npm run build")
    TOUR_LIST_BUNDLE = ""
    TOUR_DETAIL_BUNDLE = ""
    TOUR_COMPARE_BUNDLE = ""
    HAS_UI = False

# ---------------------------------------------------------------------------
# Widget definitions
# ---------------------------------------------------------------------------

MIME_TYPE = "text/html+skybridge"


@dataclass(frozen=True)
class RaynaWidget:
    identifier: str
    title: str
    template_uri: str
    invoking: str
    invoked: str
    html: str
    response_text: str


def _make_html(root_id: str, bundle: str) -> str:
    if not HAS_UI:
        return "<div>UI not available. Build React components first.</div>"
    return f'<div id="{root_id}"></div>\n<script type="module">\n{bundle}\n</script>'


widgets: List[RaynaWidget] = [
    RaynaWidget(
        identifier="show-tours",
        title="Show Tours",
        template_uri="ui://widget/rayna-tour-list.html",
        invoking="",
        invoked="",
        html=_make_html("rayna-tour-list-root", TOUR_LIST_BUNDLE),
        response_text="",
    ),
    RaynaWidget(
        identifier="show-tour-detail",
        title="Show Tour Detail",
        template_uri="ui://widget/rayna-tour-detail.html",
        invoking="",
        invoked="",
        html=_make_html("rayna-tour-detail-root", TOUR_DETAIL_BUNDLE),
        response_text="",
    ),
    RaynaWidget(
        identifier="compare-tours",
        title="Compare Tours",
        template_uri="ui://widget/rayna-tour-compare.html",
        invoking="",
        invoked="",
        html=_make_html("rayna-tour-compare-root", TOUR_COMPARE_BUNDLE),
        response_text="",
    ),
]

WIDGETS_BY_ID: Dict[str, RaynaWidget] = {w.identifier: w for w in widgets}
WIDGETS_BY_URI: Dict[str, RaynaWidget] = {w.template_uri: w for w in widgets}

# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


class ShowToursInput(BaseModel):
    city: str | None = Field(None, description="City to search tours in (e.g. Dubai, Bangkok, Bali, Singapore)")
    category: str | None = Field(None, description="Filter by category (e.g. desert safari, cruise, theme park, adventure, cultural, food, island)")
    tour_name: str | None = Field(None, description="Specific tour name to search for — use the FULL name including time/variant qualifiers (e.g. 'evening desert safari', 'morning desert safari', 'premium desert safari', 'mega yacht cruise'). Always include qualifiers like morning/evening/premium/private/VIP.")
    max_price: float | None = Field(None, description="Maximum price in AED")
    limit: int = Field(6, description="Number of tours to show (1-12)", ge=1, le=12)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowTourDetailInput(BaseModel):
    tour_url: str | None = Field(None, description="Full URL of the tour on raynatours.com")
    tour_name: str | None = Field(None, description="Name or title of the tour to look up")
    product_id: int | None = Field(None, description="Product ID from a previous show-tours result")
    city: str | None = Field(None, description="City to help find the tour (e.g. Dubai)")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CompareToursInput(BaseModel):
    tour_names: List[str] = Field(..., description="Names of 2-4 tours to compare side by side", min_length=2, max_length=4)
    city: str | None = Field(None, description="City where the tours are located (e.g. Dubai). Helps find the correct tours.")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowHolidayPackagesInput(BaseModel):
    city: str = Field(..., description="City to search holiday packages in")
    limit: int = Field(6, description="Number of packages to show (1-12)", ge=1, le=12)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class GetVisaInfoInput(BaseModel):
    country: str = Field(..., description="Country to get visa information for (e.g. usa, uk, canada, australia)")
    limit: int = Field(10, description="Maximum number of visa products to return", ge=1, le=20)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowYachtsInput(BaseModel):
    city: str = Field(..., description="City to search yacht experiences in (e.g. Dubai, Abu Dhabi)")
    limit: int = Field(6, description="Number of yachts to show (1-12)", ge=1, le=12)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


TOOL_SCHEMAS: Dict[str, dict] = {
    "show-tours": ShowToursInput.model_json_schema(),
    "show-tour-detail": ShowTourDetailInput.model_json_schema(),
    "compare-tours": CompareToursInput.model_json_schema(),
    "show-holiday-packages": ShowHolidayPackagesInput.model_json_schema(),
    "get-visa-info": GetVisaInfoInput.model_json_schema(),
    "show-yachts": ShowYachtsInput.model_json_schema(),
}

_NO_NARRATE = (
    " CRITICAL: Call this tool silently — do NOT write ANY text before calling it. "
    "No 'I'm pulling...', 'Let me fetch...', 'Loading...', 'Searching...'. "
    "Just call the tool, then present results directly."
)

TOOL_DESCRIPTIONS: Dict[str, str] = {
    "show-tours": (
        "Search and display tours and activities as visual cards. "
        "Filter by city (e.g. Dubai, Bangkok, Bali), category (e.g. Desert Safari, Theme Park), "
        "or price range. When the user asks for a SPECIFIC variant like 'evening desert safari', "
        "'morning desert safari', 'premium yacht cruise', etc., you MUST pass the full specific name "
        "in tour_name (e.g. tour_name='evening desert safari'). Do NOT drop qualifiers like "
        "morning/evening/premium/private/VIP. Returns a scrollable card grid with images, prices, and booking links."
        + _NO_NARRATE
    ),
    "show-tour-detail": (
        "Show full details for a specific tour including description, highlights, inclusions, "
        "exclusions, pricing, duration, rating, and a direct booking link."
        + _NO_NARRATE
    ),
    "compare-tours": (
        "Compare 2 to 4 tours side by side in a comparison table. "
        "Shows price, duration, rating, and highlights for each tour."
        + _NO_NARRATE
    ),
    "show-holiday-packages": (
        "Show holiday and vacation packages for a city, country, or region. "
        "Supports countries (Thailand, India), states (Kerala, Rajasthan), and cities (Delhi, Bangkok). "
        "Returns package cards with prices, durations, images, and booking links."
        + _NO_NARRATE
    ),
    "get-visa-info": (
        "Get visa requirements, fees, processing time, and documents needed for a specific country."
        + _NO_NARRATE
    ),
    "show-yachts": (
        "Search and display yacht experiences and luxury boat cruises as visual cards. "
        "Shows yacht rentals, sunset cruises, party boats, and private yacht charters. "
        "Filter by city (e.g. Dubai, Abu Dhabi). Returns a scrollable card grid with "
        "images, prices, capacity, and booking links."
        + _NO_NARRATE
    ),
}

# Per-tool annotation hints (OpenAI submission requirement)
TOOL_ANNOTATIONS: Dict[str, dict] = {
    "show-tours": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,  # calls external Rayna API
    },
    "show-tour-detail": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    "compare-tours": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    "show-holiday-packages": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    "get-visa-info": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
    "show-yachts": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    },
}

# ---------------------------------------------------------------------------
# FastMCP server
# ---------------------------------------------------------------------------

# Transport security: allow Railway/cloud hosts (their proxy handles security)
_transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

mcp = FastMCP(
    name="rayna-tours",
    instructions=(
        "SILENT TOOL CALLS: Never generate text before calling a tool. "
        "No 'I'm pulling...', 'Let me fetch...', 'Searching...', 'Loading...'. "
        "Call tools immediately, then present results. This is the #1 rule.\n\n"
        "You are a Rayna Tours travel assistant. "
        "Use MCP tools for ALL travel queries: "
        "show-tours (browsing), show-tour-detail (details), "
        "compare-tours (comparisons), show-holiday-packages (packages), "
        "get-visa-info (visa info), show-yachts (yachts).\n\n"
        "Rules:\n"
        "- Pass the FULL tour variant name in tour_name (e.g. 'evening desert safari'). "
        "Never drop qualifiers like morning/evening/premium/private/VIP.\n"
        "- Never use web search or browsing.\n"
        "- If no results: 'I could not find that in our Rayna Tours catalog. "
        "Visit https://www.raynatours.com for more options.'\n"
        "- After tool results, present information directly. No preamble, no loading messages."
    ),
    sse_path="/mcp",
    message_path="/mcp/messages",
    stateless_http=True,
    transport_security=_transport_security,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _tool_meta(widget: RaynaWidget, tool_name: str = "") -> Dict[str, Any]:
    annotations = TOOL_ANNOTATIONS.get(tool_name, {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    })
    return {
        "openai/outputTemplate": widget.template_uri,
        "openai/toolInvocation/invoking": widget.invoking,
        "openai/toolInvocation/invoked": widget.invoked,
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
        "openai/widgetDescription": widget.response_text,
        "annotations": annotations,
    }


def _resource_description(widget: RaynaWidget) -> str:
    return f"UI widget for {widget.title}"


def _embedded_widget_resource(widget: RaynaWidget) -> types.EmbeddedResource:
    return types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=widget.template_uri,
            mimeType=MIME_TYPE,
            text=widget.html,
            title=widget.title,
        ),
    )


def _error_result(msg: str) -> types.ServerResult:
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=msg)],
            isError=True,
        )
    )


def _widget_result(widget: RaynaWidget, text: str, structured: dict) -> types.ServerResult:
    widget_resource = _embedded_widget_resource(widget)
    meta: Dict[str, Any] = {
        "openai.com/widget": widget_resource.model_dump(mode="json"),
        "openai/outputTemplate": widget.template_uri,
        "openai/toolInvocation/invoking": widget.invoking,
        "openai/toolInvocation/invoked": widget.invoked,
        "openai/widgetAccessible": True,
        "openai/resultCanProduceWidget": True,
    }
    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=structured,
            _meta=meta,
        )
    )


# ---------------------------------------------------------------------------
# MCP handlers
# ---------------------------------------------------------------------------

@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    tool_list: List[types.Tool] = []

    # Widget-backed tools
    for widget in widgets:
        tool_list.append(
            types.Tool(
                name=widget.identifier,
                title=widget.title,
                description=TOOL_DESCRIPTIONS.get(widget.identifier, widget.title),
                inputSchema=TOOL_SCHEMAS[widget.identifier],
                _meta=_tool_meta(widget, widget.identifier),
            )
        )

    # Holiday packages — uses same tour list widget for rendering
    tour_list_widget = WIDGETS_BY_ID["show-tours"]
    tool_list.append(
        types.Tool(
            name="show-holiday-packages",
            title="Show Holiday Packages",
            description=TOOL_DESCRIPTIONS["show-holiday-packages"],
            inputSchema=TOOL_SCHEMAS["show-holiday-packages"],
            _meta=_tool_meta(tour_list_widget, "show-holiday-packages"),
        )
    )

    # Text-only tools (with annotations in _meta)
    tool_list.append(
        types.Tool(
            name="get-visa-info",
            title="Get Visa Information",
            description=TOOL_DESCRIPTIONS["get-visa-info"],
            inputSchema=TOOL_SCHEMAS["get-visa-info"],
            _meta={"annotations": TOOL_ANNOTATIONS["get-visa-info"]},
        )
    )

    # Yacht experiences — reuses tour list widget
    tool_list.append(
        types.Tool(
            name="show-yachts",
            title="Show Yachts",
            description=TOOL_DESCRIPTIONS["show-yachts"],
            inputSchema=TOOL_SCHEMAS["show-yachts"],
            _meta=_tool_meta(tour_list_widget, "show-yachts"),
        )
    )

    return tool_list


@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    seen_uris: set[str] = set()
    resources: List[types.Resource] = []
    for widget in widgets:
        if widget.template_uri not in seen_uris:
            seen_uris.add(widget.template_uri)
            resources.append(
                types.Resource(
                    name=widget.title,
                    title=widget.title,
                    uri=widget.template_uri,
                    description=_resource_description(widget),
                    mimeType=MIME_TYPE,
                    _meta=_tool_meta(widget, widget.identifier),
                )
            )
    return resources


@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    seen_uris: set[str] = set()
    templates: List[types.ResourceTemplate] = []
    for widget in widgets:
        if widget.template_uri not in seen_uris:
            seen_uris.add(widget.template_uri)
            templates.append(
                types.ResourceTemplate(
                    name=widget.title,
                    title=widget.title,
                    uriTemplate=widget.template_uri,
                    description=_resource_description(widget),
                    mimeType=MIME_TYPE,
                    _meta=_tool_meta(widget, widget.identifier),
                )
            )
    return templates


async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    widget = WIDGETS_BY_URI.get(str(req.params.uri))
    if widget is None:
        return types.ServerResult(
            types.ReadResourceResult(contents=[], _meta={"error": f"Unknown resource: {req.params.uri}"})
        )
    contents = [
        types.TextResourceContents(
            uri=widget.template_uri,
            mimeType=MIME_TYPE,
            text=widget.html,
            _meta=_tool_meta(widget, widget.identifier),
        )
    ]
    return types.ServerResult(types.ReadResourceResult(contents=contents))


mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


async def _handle_show_tours(arguments: dict) -> types.ServerResult:
    payload = ShowToursInput.model_validate(arguments)
    print(f"\n[show-tours] city={payload.city!r}, category={payload.category!r}, tour_name={payload.tour_name!r}, limit={payload.limit}")
    widget = WIDGETS_BY_ID["show-tours"]
    client = RaynaApiClient()
    city_name = payload.city or ""
    cards: list[dict] = []

    async with aiohttp.ClientSession() as session:
        try:
            search_city = payload.city or "Dubai"
            city_info = await client.resolve_city_info(session, search_city)
            print(f"[show-tours] Resolved city '{search_city}' -> {city_info}")
            if city_info:
                city_id, city_name_resolved, country_name = city_info
                city_name = city_name or city_name_resolved
                # Use enriched-feed city endpoint for full data (images, reviews, etc.)
                enriched_products = await client.get_enriched_city_products(
                    session, city_id, city_name_resolved, country_name, product_type="tour"
                )
                print(f"[show-tours] Enriched-feed returned {len(enriched_products)} products")
                if enriched_products:
                    cards = [format_enriched_tour_card(p, city_name) for p in enriched_products]
                    cards = [c for c in cards if c.get("title") and c["title"] != "Tour"]
                # Fallback to basic city/products if enriched-feed returns nothing
                if not cards:
                    print("[show-tours] Enriched-feed empty, falling back to city/products")
                    tours_raw = await client.get_city_products(session, city_id, limit=200)
                    if tours_raw and not _is_transfers_only(tours_raw):
                        cards = [format_tour_card(t, city_name) for t in tours_raw]
        except Exception as e:
            print(f"[show-tours] API error: {e}")

    print(f"[show-tours] Formatted {len(cards)} cards")

    # 2. No results at all
    if not cards:
        return _error_result("No tours found. Please try a different city or category.")

    # Apply tour_name filter FIRST (more specific), then category filter
    search_term = payload.tour_name or payload.category
    if search_term:
        term_lower = search_term.lower()
        term_words = term_lower.split()
        pre_filter_count = len(cards)

        # Contradicting qualifiers — if tour_name says "evening", reject "morning" matches
        _QUALIFIER_OPPOSITES = {
            "evening": "morning", "morning": "evening",
            "private": "shared", "shared": "private",
            "premium": "standard", "standard": "premium",
            "vip": "standard", "luxury": "standard",
        }
        reject_words = set()
        if payload.tour_name:
            for word in payload.tour_name.lower().split():
                opposite = _QUALIFIER_OPPOSITES.get(word)
                if opposite:
                    reject_words.add(opposite)
        if reject_words:
            print(f"[show-tours] Rejecting cards with contradicting qualifiers: {reject_words}")

        # Expand category to related keywords (e.g. "adventure" → ["zipline", "skydiving", ...])
        category_synonyms: list[str] = []
        if payload.category:
            cat_lower = payload.category.lower()
            for cat_name, keywords in CATEGORY_KEYWORDS.items():
                if cat_lower in cat_name.lower() or cat_name.lower() in cat_lower:
                    category_synonyms = [kw.lower() for kw in keywords]
                    print(f"[show-tours] Expanded category '{payload.category}' -> synonyms: {category_synonyms}")
                    break

        # Score each card: higher score = better match
        scored_cards = []
        for c in cards:
            title_lower = c["title"].lower()
            cat_field = c.get("category", "").lower()
            desc_lower = (c.get("description") or "").lower()[:300]

            # Reject contradicting qualifiers (e.g. "morning" when user asked "evening")
            if reject_words and any(rw in title_lower for rw in reject_words):
                print(f"  REJECTED (contradicting qualifier): {c['title']}")
                continue

            score = 0
            # Exact substring match in title (best)
            if term_lower in title_lower:
                score = 3
            # All words present in title
            elif all(w in title_lower for w in term_words):
                score = 2
            # Category field match (broadest)
            elif term_lower in cat_field or (payload.category and payload.category.lower() in cat_field):
                score = 1
            # Also check category words in title (fallback for category-only)
            elif payload.category and all(w in title_lower for w in payload.category.lower().split()):
                score = 1
            # Category synonym match in title or description (e.g. "adventure" → "quad bike" in title)
            elif category_synonyms and any(syn in title_lower for syn in category_synonyms):
                score = 1
            elif category_synonyms and any(syn in desc_lower for syn in category_synonyms):
                score = 1
            if score > 0:
                scored_cards.append((score, c))

        # Sort by score descending so best matches come first
        scored_cards.sort(key=lambda x: x[0], reverse=True)
        cards = [c for _, c in scored_cards]

        print(f"[show-tours] Filter '{search_term}': {pre_filter_count} -> {len(cards)} cards")
        if cards:
            for sc, c in scored_cards[:5]:
                print(f"  Matched (score={sc}): {c['title']} | url={c.get('url','')}")

    # Apply price filter
    if payload.max_price is not None:
        cards = [c for c in cards if c["currentPrice"] and c["currentPrice"] <= payload.max_price]

    if not cards:
        return _error_result("No tours found matching your criteria. Please try different search terms.")

    cards = cards[: payload.limit]

    title = f"Tours in {city_name}" if city_name else "Popular Tours"
    if payload.category:
        title = f"{payload.category.title()} {title}"

    structured = {
        "tours": cards,
        "title": title,
        "subtitle": f"{len(cards)} experiences found",
        "totalResults": len(cards),
        "dataSource": "api",
    }

    text_lines = [f"Found {len(cards)} tours:"]
    for i, c in enumerate(cards[:6], 1):
        price_str = f"{c['currency']} {c['currentPrice']}"
        text_lines.append(f"{i}. {c['title']} - {price_str} ({c.get('duration', 'N/A')}) - {c.get('url', '')}")

    return _widget_result(widget, "\n".join(text_lines), structured)


async def _handle_show_tour_detail(arguments: dict) -> types.ServerResult:
    payload = ShowTourDetailInput.model_validate(arguments)
    print(f"\n[show-tour-detail] tour_url={payload.tour_url!r}, tour_name={payload.tour_name!r}, product_id={payload.product_id!r}, city={payload.city!r}")
    widget = WIDGETS_BY_ID["show-tour-detail"]
    client = RaynaApiClient()
    detail: dict[str, Any] = {}

    async with aiohttp.ClientSession() as session:
        # Strategy 1: product_id → enriched-feed directly
        if payload.product_id:
            try:
                enriched = await client.get_enriched_product(session, payload.product_id, "tour")
                if enriched and enriched.get("_enriched"):
                    detail = format_enriched_tour_detail(enriched)
                    print(f"[show-tour-detail] Got enriched detail for product_id={payload.product_id}")
            except Exception as e:
                print(f"[show-tour-detail] Enriched-feed error: {e}")

        # Strategy 2: tour_url → extract product ID from URL, then enrich
        if not detail and payload.tour_url:
            try:
                pid_match = re.search(r"-e?-?(\d+)$", payload.tour_url.rstrip("/"))
                if not pid_match:
                    pid_match = re.search(r"productId=(\d+)", payload.tour_url)
                if pid_match:
                    pid = pid_match.group(1)
                    enriched = await client.get_enriched_product(session, pid, "tour")
                    if enriched and enriched.get("_enriched"):
                        detail = format_enriched_tour_detail(enriched)
                        print(f"[show-tour-detail] Enriched from URL, pid={pid}")
            except Exception as e:
                print(f"[show-tour-detail] URL extraction error: {e}")

        # Strategy 3: tour_name → search enriched city feed, find best match
        if not detail and payload.tour_name:
            name_lower = payload.tour_name.lower()

            # Determine cities to search: explicit city, auto-detected from name, then Dubai fallback
            cities_to_try: list[str] = []
            if payload.city:
                cities_to_try.append(payload.city)
            detected_city = detect_city_from_tour_name(payload.tour_name)
            if detected_city and detected_city not in cities_to_try:
                cities_to_try.append(detected_city)
                print(f"[show-tour-detail] Auto-detected city '{detected_city}' from tour name")
            if "Dubai" not in cities_to_try:
                cities_to_try.append("Dubai")

            # Search each city, trying both tour and holiday product types
            for city in cities_to_try:
                if detail:
                    break
                for product_type in ("tour", "holiday"):
                    if detail:
                        break
                    try:
                        city_info = await client.resolve_city_info(session, city, product_type)
                        if not city_info:
                            continue
                        city_id, city_name_resolved, country_name = city_info

                        # Try enriched city feed first (has full data with inclusions/exclusions)
                        products = await client.get_enriched_city_products(
                            session, city_id, city_name_resolved, country_name, product_type=product_type
                        )
                        print(f"[show-tour-detail] Enriched city feed ({product_type}) returned {len(products)} products for '{city}'")

                        best_match = None
                        best_score = 0
                        for p in products:
                            p_name = (p.get("detail_title") or p.get("name") or "").lower()
                            if name_lower in p_name:
                                score = 3
                            elif all(w in p_name for w in name_lower.split()):
                                score = 2
                            else:
                                score = 0
                            if score > best_score:
                                best_score = score
                                best_match = p

                        if best_match:
                            detail = format_enriched_tour_detail(best_match)
                            print(f"[show-tour-detail] Found in enriched {product_type} feed for '{city}': {best_match.get('detail_title') or best_match.get('name')}")
                            break
                    except Exception as e:
                        print(f"[show-tour-detail] Search error ({city}/{product_type}): {e}")

            # Last resort: try basic product search + individual enrichment
            if not detail:
                for city in cities_to_try:
                    if detail:
                        break
                    try:
                        city_info = await client.resolve_city_info(session, city)
                        if not city_info:
                            continue
                        city_id = city_info[0]
                        basic_products = await client.get_city_products(session, city_id, limit=200)
                        for p in basic_products:
                            p_name = (p.get("name") or p.get("title") or "").lower()
                            if name_lower in p_name or all(w in p_name for w in name_lower.split()):
                                pid = p.get("id") or p.get("productId")
                                if pid:
                                    try:
                                        enriched = await client.get_enriched_product(session, pid, "tour")
                                        if enriched and enriched.get("_enriched"):
                                            detail = format_enriched_tour_detail(enriched)
                                            print(f"[show-tour-detail] Found via basic search + enrich, pid={pid}")
                                            break
                                    except Exception:
                                        pass
                            if detail:
                                break
                    except Exception as e:
                        print(f"[show-tour-detail] Basic search error ({city}): {e}")

    if not detail:
        return _error_result("Tour not found. Please provide a valid tour name, URL, or product ID.")

    text_parts = [f"{detail['title']} in {detail['location']} - {detail['currency']} {detail['currentPrice']}"]
    if detail.get("url"):
        text_parts.append(f"Book here: {detail['url']}")
    if detail.get("duration"):
        text_parts.append(f"Duration: {detail['duration']}")
    if detail.get("itinerary"):
        text_parts.append(f"\nItinerary:\n{detail['itinerary']}")
    if detail.get("inclusions"):
        inc = detail["inclusions"]
        inc_text = ", ".join(inc) if isinstance(inc, list) else str(inc)
        text_parts.append(f"\nInclusions:\n{inc_text}")
    if detail.get("exclusions"):
        exc = detail["exclusions"]
        exc_text = ", ".join(exc) if isinstance(exc, list) else str(exc)
        text_parts.append(f"\nExclusions:\n{exc_text}")
    if detail.get("highlights"):
        hl = detail["highlights"]
        hl_text = ", ".join(hl) if isinstance(hl, list) else str(hl)
        text_parts.append(f"\nHighlights:\n{hl_text}")
    if detail.get("description"):
        text_parts.append(f"\nDescription:\n{detail['description'][:500]}")
    text = "\n".join(text_parts)
    return _widget_result(widget, text, detail)


async def _handle_compare_tours(arguments: dict) -> types.ServerResult:
    payload = CompareToursInput.model_validate(arguments)
    print(f"\n[compare-tours] names={payload.tour_names!r}, city={payload.city!r}")
    widget = WIDGETS_BY_ID["compare-tours"]
    client = RaynaApiClient()
    found_tours: list[dict] = []

    async with aiohttp.ClientSession() as session:
        city = payload.city or "Dubai"
        city_info = await client.resolve_city_info(session, city)
        if not city_info:
            return _error_result(f"Could not find city '{city}'. Please try a different city.")

        city_id, city_name_resolved, country_name = city_info
        # Use enriched city feed for full data
        products = await client.get_enriched_city_products(
            session, city_id, city_name_resolved, country_name, product_type="tour"
        )
        print(f"[compare-tours] Enriched city feed returned {len(products)} products for '{city}'")

        for tour_name in payload.tour_names:
            name_lower = tour_name.lower()
            best_match = None
            best_score = 0
            for p in products:
                p_name = (p.get("detail_title") or p.get("name") or "").lower()
                if name_lower in p_name:
                    score = 3
                elif all(w in p_name for w in name_lower.split()):
                    score = 2
                else:
                    score = 0
                if score > best_score:
                    best_score = score
                    best_match = p

            if best_match:
                found_tours.append(format_enriched_tour_card(best_match, city))
                print(f"[compare-tours] Matched '{tour_name}': {best_match.get('detail_title') or best_match.get('name')}")

    if len(found_tours) < 2:
        return _error_result(
            f"Could only find {len(found_tours)} tours. Need at least 2 to compare. "
            f"Try names like 'Dubai Desert Safari', 'Burj Khalifa', 'Phi Phi Island'. "
            f"Also provide the city parameter for better matching."
        )

    # Build comparison stats
    stat_names = [
        ("Price (AED)", "currentPrice", "lower"),
        ("Rating", "rating", "higher"),
        ("Duration", "duration", None),
        ("Category", "category", None),
        ("Location", "location", None),
        ("R-Points", "rPoints", "higher"),
    ]

    stats: list[dict] = []
    for label, key, direction in stat_names:
        values = []
        for t in found_tours:
            v = t.get(key)
            values.append(v if v is not None else "N/A")

        better = None
        if direction and all(isinstance(v, (int, float)) for v in values):
            if direction == "lower":
                best_idx = values.index(min(values))
            else:
                best_idx = values.index(max(values))
            better = found_tours[best_idx]["title"]

        display_values = []
        for v in values:
            if isinstance(v, float):
                display_values.append(f"{v:.1f}" if v != int(v) else str(int(v)))
            else:
                display_values.append(str(v))

        stats.append({"name": label, "values": display_values, "better": better})

    structured = {
        "tours": found_tours,
        "comparison": {"stats": stats},
    }

    names = " vs ".join(t["title"] for t in found_tours)
    return _widget_result(widget, f"Comparing: {names}", structured)


async def _handle_show_holiday_packages(arguments: dict) -> types.ServerResult:
    payload = ShowHolidayPackagesInput.model_validate(arguments)
    print(f"\n[show-holiday-packages] city={payload.city!r}, limit={payload.limit}")
    widget = WIDGETS_BY_ID["show-tours"]  # Reuse the tour list widget
    client = RaynaApiClient()
    cards: list[dict] = []

    # 1. Try live API — resolve region/country to city IDs
    async with aiohttp.ClientSession() as session:
        try:
            city_pairs = await client.resolve_region_city_ids(session, payload.city, product_type="holiday")
            print(f"[show-holiday-packages] Resolved '{payload.city}' -> {city_pairs}")
            for city_id, city_name in city_pairs:
                raw = await client.get_city_holiday(session, city_id)
                print(f"[show-holiday-packages] {city_name} (id={city_id}): {len(raw)} raw products")
                city_cards = [format_tour_card(t, city_name) for t in raw if isinstance(t, dict)]
                city_cards = [c for c in city_cards if c.get("title") and c["title"] != "Tour"]
                cards.extend(city_cards)
        except Exception as e:
            print(f"[show-holiday-packages] API error: {e}")

    print(f"[show-holiday-packages] API produced {len(cards)} cards")
    if cards:
        for c in cards[:3]:
            print(f"  {c['title']} | price={c['currentPrice']} | url={c.get('url','')}")

    if not cards:
        return _error_result(f"No holiday packages found for {payload.city}.")

    cards = cards[: payload.limit]
    title = f"Holiday Packages in {payload.city}"

    structured = {
        "tours": cards,
        "title": title,
        "subtitle": f"{len(cards)} packages found",
        "totalResults": len(cards),
        "dataSource": "api",
    }

    text = f"Found {len(cards)} holiday packages in {payload.city}"
    return _widget_result(widget, text, structured)


async def _handle_get_visa_info(arguments: dict) -> types.ServerResult:
    payload = GetVisaInfoInput.model_validate(arguments)
    client = RaynaApiClient()
    visas: list[dict] = []

    async with aiohttp.ClientSession() as session:
        try:
            visas = await client.get_visas(session, payload.country, payload.limit)
        except Exception:
            pass

    if not visas:
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"No visa information found for '{payload.country}'. Visit https://www.raynatours.com for details.",
                    )
                ],
                isError=False,
            )
        )

    lines = [f"Visa information for {payload.country.upper()}:\n"]
    for v in visas:
        name = v.get("name") or v.get("title") or "Visa"
        price = v.get("price") or v.get("amount") or "N/A"
        visa_type = v.get("type") or v.get("visa_type") or ""
        processing = v.get("processing_time") or v.get("processingTime") or ""
        lines.append(f"- {name}")
        if visa_type:
            lines.append(f"  Type: {visa_type}")
        if price != "N/A":
            lines.append(f"  Price: AED {price}")
        if processing:
            lines.append(f"  Processing: {processing}")
        lines.append("")

    lines.append(f"\nFor more details: https://www.raynatours.com")

    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(lines))],
            isError=False,
        )
    )


async def _handle_show_yachts(arguments: dict) -> types.ServerResult:
    """Show yacht experiences for a city."""
    payload = ShowYachtsInput.model_validate(arguments)
    print(f"\n[show-yachts] city={payload.city!r}, limit={payload.limit}")
    widget = WIDGETS_BY_ID["show-tours"]  # Reuse tour list widget
    client = RaynaApiClient()
    cards: list[dict] = []

    _BOAT_KEYWORDS = ("yacht", "cruise", "boat", "dhow", "catamaran", "sailing", "ferry", "marina")

    async with aiohttp.ClientSession() as session:
        # 1. Try dedicated yacht endpoint
        try:
            city_info = await client.resolve_city_info(session, payload.city, product_type="yacht")
            print(f"[show-yachts] Resolved '{payload.city}' (yacht) -> {city_info}")
            if city_info:
                city_id, city_name_resolved, country_name = city_info
                enriched = await client.get_enriched_city_products(
                    session, city_id, city_name_resolved, country_name, product_type="yacht"
                )
                print(f"[show-yachts] Enriched yacht feed returned {len(enriched)} products")
                if enriched:
                    cards = [format_enriched_tour_card(y, payload.city) for y in enriched]
                    cards = [c for c in cards if c.get("title") and c["title"] != "Tour"]
                if not cards:
                    raw_yachts = await client.get_city_yacht(session, city_id, limit=payload.limit * 2)
                    print(f"[show-yachts] Basic yacht endpoint returned {len(raw_yachts)} products")
                    cards = [format_tour_card(y, payload.city) for y in raw_yachts if isinstance(y, dict)]
                    cards = [c for c in cards if c.get("title") and c["title"] != "Tour"]
        except Exception as e:
            print(f"[show-yachts] Yacht endpoint error: {e}")

        # 2. Fallback: search tour products for yacht/cruise/boat keywords
        if not cards:
            try:
                city_info = await client.resolve_city_info(session, payload.city, product_type="tour")
                print(f"[show-yachts] Fallback: resolved '{payload.city}' (tour) -> {city_info}")
                if city_info:
                    city_id, city_name_resolved, country_name = city_info
                    all_tours = await client.get_enriched_city_products(
                        session, city_id, city_name_resolved, country_name, product_type="tour"
                    )
                    print(f"[show-yachts] Fallback: enriched tour feed returned {len(all_tours)} products")
                    for t in all_tours:
                        t_name = (t.get("detail_title") or t.get("name") or "").lower()
                        t_desc = (t.get("description_text") or "").lower()[:200]
                        if any(kw in t_name or kw in t_desc for kw in _BOAT_KEYWORDS):
                            cards.append(format_enriched_tour_card(t, payload.city))
                    cards = [c for c in cards if c.get("title") and c["title"] != "Tour"]
                    print(f"[show-yachts] Fallback: found {len(cards)} boat/cruise tours")
            except Exception as e:
                print(f"[show-yachts] Fallback tour search error: {e}")

        # 3. Last resort: try cruise endpoint
        if not cards:
            try:
                city_info = await client.resolve_city_info(session, payload.city, product_type="cruise")
                if city_info:
                    city_id = city_info[0]
                    raw_cruises = await client.get_city_cruise(session, city_id, limit=payload.limit * 2)
                    print(f"[show-yachts] Cruise endpoint returned {len(raw_cruises)} products")
                    cards = [format_tour_card(c, payload.city) for c in raw_cruises if isinstance(c, dict)]
                    cards = [c for c in cards if c.get("title") and c["title"] != "Tour"]
            except Exception as e:
                print(f"[show-yachts] Cruise endpoint error: {e}")

    if not cards:
        return _error_result(f"No yacht or cruise experiences found in {payload.city}.")

    cards = cards[: payload.limit]
    title = f"Yacht Experiences in {payload.city}"

    structured = {
        "tours": cards,
        "title": title,
        "subtitle": f"{len(cards)} yacht experiences found",
        "totalResults": len(cards),
        "dataSource": "api",
    }

    text_lines = [f"Found {len(cards)} yacht experiences in {payload.city}:"]
    for i, c in enumerate(cards[:6], 1):
        price_str = f"{c['currency']} {c['currentPrice']}"
        text_lines.append(f"{i}. {c['title']} - {price_str} ({c.get('duration', 'N/A')}) - {c.get('url', '')}")

    return _widget_result(widget, "\n".join(text_lines), structured)


# Route tool calls
async def _call_tool_request(req: types.CallToolRequest) -> types.ServerResult:
    tool_name = req.params.name
    arguments = req.params.arguments or {}

    try:
        if tool_name == "show-tours":
            return await _handle_show_tours(arguments)
        elif tool_name == "show-tour-detail":
            return await _handle_show_tour_detail(arguments)
        elif tool_name == "compare-tours":
            return await _handle_compare_tours(arguments)
        elif tool_name == "show-holiday-packages":
            return await _handle_show_holiday_packages(arguments)
        elif tool_name == "get-visa-info":
            return await _handle_get_visa_info(arguments)
        elif tool_name == "show-yachts":
            return await _handle_show_yachts(arguments)
        else:
            return _error_result(f"Unknown tool: {tool_name}")
    except ValidationError as exc:
        return _error_result(f"Input validation error: {exc.errors()}")
    except Exception as exc:
        return _error_result(f"Error executing {tool_name}: {str(exc)}")


mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool_request

# ---------------------------------------------------------------------------
# HTTP app
# ---------------------------------------------------------------------------

app = mcp.streamable_http_app()

# CORS
try:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
except Exception:
    pass

# Health and info routes
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route


OPENAI_VERIFICATION_TOKEN = os.getenv(
    "OPENAI_VERIFICATION_TOKEN",
    "ieGBA_N4IZXhzsMO_EQQnRt-iT3Dv_42ouBWcx7aWB4",
)


async def openai_verification(request):
    return PlainTextResponse(OPENAI_VERIFICATION_TOKEN)


async def health_check(request):
    return JSONResponse({"status": "healthy", "server": "rayna-tours"})


async def server_info(request):
    return JSONResponse(
        {
            "name": "rayna-tours",
            "version": "2.0.0",
            "description": "Rayna Tours travel assistant — browse tours, yachts, holiday packages, compare activities, and get visa info across 50+ destinations.",
            "author": "Rayna Tours",
            "homepage": "https://www.raynatours.com",
            "support": "https://www.raynatours.com",
            "pattern": "OpenAI Apps SDK",
            "protocol": "MCP (Streamable HTTP)",
            "ui": "React",
            "widgets": len(set(w.template_uri for w in widgets)),
            "tools": len(TOOL_SCHEMAS),
            "api": "https://data-projects-flax.vercel.app/api",
        }
    )


app.routes.extend(
    [
        Route("/health", health_check),
        Route("/info", server_info),
        Route("/.well-known/openai-apps-challenge", openai_verification),
    ]
)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    print("=" * 60)
    print("  Rayna Tours MCP Server with React UI")
    print("=" * 60)
    print(f"\n  Endpoints:")
    print(f"  - MCP:    http://0.0.0.0:{port}/mcp")
    print(f"  - Health: http://0.0.0.0:{port}/health")
    print(f"  - Info:   http://0.0.0.0:{port}/info")
    widget_count = len(set(w.template_uri for w in widgets))
    print(f"\n  UI Widgets: {widget_count}")
    for widget in widgets:
        print(f"  - {widget.title} ({widget.identifier})")
    ui_status = "Loaded" if HAS_UI else "Not built"
    print(f"\n  React Bundles: {ui_status}")
    print(f"\n  For ChatGPT: http://localhost:{port}/mcp")
    print("  With ngrok: https://YOUR-URL.ngrok-free.app/mcp")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
