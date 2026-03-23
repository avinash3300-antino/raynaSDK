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

# RAG engine (optional — gracefully degrades if not configured)
try:
    from rag_engine import (
        search_all as rag_search_all,
        search_tours as rag_search_tours,
        dedupe_by_parent as rag_dedupe,
        format_rag_tour_card,
        is_available as rag_is_available,
    )
    HAS_RAG = rag_is_available()
except ImportError:
    HAS_RAG = False

from rayna_utils import (
    RaynaApiClient,
    format_tour_card,
    _is_transfers_only,
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
        invoking="Searching tours...",
        invoked="Showing tour list",
        html=_make_html("rayna-tour-list-root", TOUR_LIST_BUNDLE),
        response_text="Displayed Rayna Tours list!",
    ),
    RaynaWidget(
        identifier="show-tour-detail",
        title="Show Tour Detail",
        template_uri="ui://widget/rayna-tour-detail.html",
        invoking="Loading tour details...",
        invoked="Showing tour details",
        html=_make_html("rayna-tour-detail-root", TOUR_DETAIL_BUNDLE),
        response_text="Displayed tour details!",
    ),
    RaynaWidget(
        identifier="compare-tours",
        title="Compare Tours",
        template_uri="ui://widget/rayna-tour-compare.html",
        invoking="Comparing tours...",
        invoked="Showing tour comparison",
        html=_make_html("rayna-tour-compare-root", TOUR_COMPARE_BUNDLE),
        response_text="Displayed tour comparison!",
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
    max_price: float | None = Field(None, description="Maximum price in AED")
    limit: int = Field(6, description="Number of tours to show (1-12)", ge=1, le=12)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowTourDetailInput(BaseModel):
    tour_url: str | None = Field(None, description="Full URL of the tour on raynatours.com")
    tour_name: str | None = Field(None, description="Name or title of the tour to look up")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CompareToursInput(BaseModel):
    tour_names: List[str] = Field(..., description="Names of 2-4 tours to compare side by side", min_length=2, max_length=4)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ShowHolidayPackagesInput(BaseModel):
    city: str = Field(..., description="City to search holiday packages in")
    limit: int = Field(6, description="Number of packages to show (1-12)", ge=1, le=12)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class GetVisaInfoInput(BaseModel):
    country: str = Field(..., description="Country to get visa information for (e.g. usa, uk, canada, australia)")
    limit: int = Field(10, description="Maximum number of visa products to return", ge=1, le=20)
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AskRaynaInput(BaseModel):
    question: str = Field(..., description="Natural language question about tours, destinations, booking, policies, or travel tips")
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


TOOL_SCHEMAS: Dict[str, dict] = {
    "show-tours": ShowToursInput.model_json_schema(),
    "show-tour-detail": ShowTourDetailInput.model_json_schema(),
    "compare-tours": CompareToursInput.model_json_schema(),
    "show-holiday-packages": ShowHolidayPackagesInput.model_json_schema(),
    "get-visa-info": GetVisaInfoInput.model_json_schema(),
    "ask-rayna": AskRaynaInput.model_json_schema(),
}

TOOL_DESCRIPTIONS: Dict[str, str] = {
    "show-tours": (
        "Search and display tours and activities as visual cards. "
        "Filter by city (e.g. Dubai, Bangkok, Bali), category (e.g. Desert Safari, Theme Park), "
        "or price range. Returns a scrollable card grid with images, prices, and booking links."
    ),
    "show-tour-detail": (
        "Show full details for a specific tour including description, highlights, inclusions, "
        "exclusions, pricing, duration, rating, and a direct booking link."
    ),
    "compare-tours": (
        "Compare 2 to 4 tours side by side in a comparison table. "
        "Shows price, duration, rating, and highlights for each tour."
    ),
    "show-holiday-packages": (
        "Show holiday and vacation packages for a city, country, or region. "
        "Supports countries (Thailand, India), states (Kerala, Rajasthan), and cities (Delhi, Bangkok). "
        "Returns package cards with prices, durations, images, and booking links."
    ),
    "get-visa-info": "Get visa requirements, fees, processing time, and documents needed for a specific country.",
    "ask-rayna": (
        "Ask any question about Rayna Tours — destinations, booking policies, "
        "cancellation, what to wear, best time to visit, group discounts, or "
        "get personalized tour recommendations. Uses knowledge base search."
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
    "ask-rayna": {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,  # calls Pinecone + OpenAI
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
        "You are a Rayna Tours travel assistant. "
        "You MUST use the provided MCP tools to answer ALL travel, tour, and activity related queries. "
        "Use show-tours for browsing tours, show-tour-detail for specific tour info, "
        "compare-tours for comparisons, show-holiday-packages for packages, "
        "get-visa-info for visa information, and ask-rayna for general questions "
        "about booking policies, cancellations, what to wear, best time to visit, "
        "group discounts, travel tips, or personalized recommendations. "
        "NEVER use web search, browsing, or any other external tools. "
        "If the MCP tools return no results, respond with: "
        "'I could not find that information in our Rayna Tours catalog. "
        "Please visit https://www.raynatours.com for more options.' "
        "Do NOT fall back to web search or other sources under any circumstances."
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

    # RAG-powered Q&A tool
    if HAS_RAG:
        tool_list.append(
            types.Tool(
                name="ask-rayna",
                title="Ask Rayna",
                description=TOOL_DESCRIPTIONS["ask-rayna"],
                inputSchema=TOOL_SCHEMAS["ask-rayna"],
                _meta={"annotations": TOOL_ANNOTATIONS["ask-rayna"]},
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
    widget = WIDGETS_BY_ID["show-tours"]
    client = RaynaApiClient()
    tours_raw: list[dict] = []
    data_source = "api"
    city_name = payload.city or ""

    # 1. Try live API first
    async with aiohttp.ClientSession() as session:
        try:
            if payload.city:
                city_id = await client.resolve_city_id(session, payload.city)
                if city_id:
                    tours_raw = await client.get_city_products(session, city_id)
                    city_name = payload.city
            else:
                city_id = await client.resolve_city_id(session, "Dubai")
                if city_id:
                    tours_raw = await client.get_city_products(session, city_id)
                    city_name = "Dubai"
        except Exception:
            tours_raw = []

    # Format API results
    cards: list[dict] = []
    if tours_raw and not _is_transfers_only(tours_raw):
        cards = [format_tour_card(t, city_name) for t in tours_raw]

    # 2. Fallback to RAG (Pinecone) if API returned nothing
    if not cards and HAS_RAG:
        data_source = "rag"
        query = payload.city or payload.category or "popular tours"
        if payload.city and payload.category:
            query = f"{payload.category} tours in {payload.city}"
        elif payload.city:
            query = f"tours in {payload.city}"
        elif payload.category:
            query = f"{payload.category} tours"

        rag_results = rag_search_tours(query, top_k=payload.limit * 3)
        deduped = rag_dedupe(rag_results)
        cards = [format_rag_tour_card(r["metadata"]) for r in deduped]

    # 3. No results at all
    if not cards:
        return _error_result("No tours found. Please try a different city or category.")

    # Apply category filter
    if payload.category:
        cat_lower = payload.category.lower()
        cat_words = cat_lower.split()
        cards = [
            c for c in cards
            if cat_lower in c.get("category", "").lower()
            or cat_lower in c["title"].lower()
            or all(w in c["title"].lower() for w in cat_words)
        ]

    # Apply price filter
    if payload.max_price is not None:
        cards = [c for c in cards if c["currentPrice"] and c["currentPrice"] <= payload.max_price]

    # Fallback to RAG if filters eliminated all API results
    if not cards and HAS_RAG:
        data_source = "rag"
        query = payload.category or payload.city or "popular tours"
        if payload.city and payload.category:
            query = f"{payload.category} in {payload.city}"
        rag_results = rag_search_tours(query, top_k=payload.limit * 3)
        deduped = rag_dedupe(rag_results)
        cards = [format_rag_tour_card(r["metadata"]) for r in deduped]

    cards = cards[: payload.limit]

    title = f"Tours in {city_name}" if city_name else "Popular Tours"
    if payload.category:
        title = f"{payload.category.title()} {title}"

    structured = {
        "tours": cards,
        "title": title,
        "subtitle": f"{len(cards)} experiences found",
        "totalResults": len(cards),
        "dataSource": data_source,
    }

    text_lines = [f"Found {len(cards)} tours:"]
    for i, c in enumerate(cards[:6], 1):
        price_str = f"{c['currency']} {c['currentPrice']}"
        text_lines.append(f"{i}. {c['title']} - {price_str} ({c.get('duration', 'N/A')}) - {c.get('url', '')}")

    return _widget_result(widget, "\n".join(text_lines), structured)


async def _handle_show_tour_detail(arguments: dict) -> types.ServerResult:
    payload = ShowTourDetailInput.model_validate(arguments)
    widget = WIDGETS_BY_ID["show-tour-detail"]

    detail: dict[str, Any] = {}

    # 1. Try API first if URL provided
    if payload.tour_url:
        client = RaynaApiClient()
        async with aiohttp.ClientSession() as session:
            try:
                raw = await client.get_product_details(session, payload.tour_url)
                if raw:
                    detail = {
                        "title": raw.get("name") or raw.get("title") or "Tour",
                        "description": raw.get("description") or raw.get("shortDescription") or "",
                        "image": raw.get("image", {}).get("src", "") if isinstance(raw.get("image"), dict) else raw.get("image", ""),
                        "location": raw.get("city") or raw.get("cityName") or "",
                        "category": raw.get("category") or "",
                        "currentPrice": float(raw.get("salePrice") or raw.get("price") or raw.get("amount") or 0),
                        "originalPrice": float(raw.get("amount") or raw.get("normalPrice") or 0) if raw.get("amount") else None,
                        "currency": raw.get("currency", "AED"),
                        "duration": raw.get("duration") if isinstance(raw.get("duration"), str) else None,
                        "highlights": raw.get("highlights") or [],
                        "inclusions": raw.get("inclusions") or [],
                        "exclusions": raw.get("exclusions") or [],
                        "itinerary": raw.get("itinerary") or raw.get("itineraryDetails") or "",
                        "rating": float(raw.get("averageRating") or 0) if raw.get("averageRating") else None,
                        "reviewCount": raw.get("reviewCount"),
                        "url": payload.tour_url,
                        "rPoints": int(round(float(raw.get("salePrice") or raw.get("price") or 0) * 0.01 / 100) * 100),
                    }
            except Exception:
                pass

    # 2. Fallback to RAG search by name
    if not detail and payload.tour_name and HAS_RAG:
        # Search tours first, then all types (holiday packages have pageType="holiday")
        rag_results = rag_search_tours(payload.tour_name, top_k=5)
        deduped = rag_dedupe(rag_results)
        if not deduped:
            rag_results = rag_search_all(payload.tour_name, top_k=5)
            deduped = rag_dedupe(rag_results)
        if deduped:
            meta = deduped[0]["metadata"]
            card = format_rag_tour_card(meta)
            detail = {
                "title": card["title"],
                "description": card["description"],
                "image": card["image"],
                "location": card["location"],
                "category": card["category"],
                "currentPrice": card["currentPrice"],
                "originalPrice": None,
                "currency": card["currency"],
                "duration": card["duration"],
                "highlights": meta.get("highlights") or [],
                "inclusions": meta.get("inclusions") or [],
                "exclusions": meta.get("exclusions") or [],
                "rating": None,
                "reviewCount": None,
                "url": card["url"],
                "rPoints": card["rPoints"],
                "itinerary": meta.get("itinerary", ""),
            }

    if not detail:
        return _error_result("Tour not found. Please provide a valid tour URL or name.")

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
    widget = WIDGETS_BY_ID["compare-tours"]

    found_tours: list[dict] = []
    if HAS_RAG:
        for name in payload.tour_names:
            rag_results = rag_search_tours(name, top_k=3)
            deduped = rag_dedupe(rag_results)
            if deduped:
                found_tours.append(format_rag_tour_card(deduped[0]["metadata"]))

    if len(found_tours) < 2:
        return _error_result(
            f"Could only find {len(found_tours)} tours. Need at least 2 to compare. "
            f"Try names like 'Dubai Desert Safari', 'Burj Khalifa', 'Phi Phi Island'."
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
    widget = WIDGETS_BY_ID["show-tours"]  # Reuse the tour list widget
    client = RaynaApiClient()
    cards: list[dict] = []
    data_source = "api"

    # 1. Try live API — resolve region/country to city IDs
    async with aiohttp.ClientSession() as session:
        try:
            city_pairs = await client.resolve_region_city_ids(session, payload.city, product_type="holiday")
            for city_id, city_name in city_pairs:
                raw = await client.get_city_holiday(session, city_id)
                city_cards = [format_tour_card(t, city_name) for t in raw if isinstance(t, dict)]
                city_cards = [c for c in city_cards if c.get("title") and c["title"] != "Tour"]
                cards.extend(city_cards)
        except Exception:
            pass

    # 2. Fallback to RAG
    if not cards and HAS_RAG:
        data_source = "rag"
        rag_results = rag_search_tours(f"holiday package {payload.city}", top_k=payload.limit * 3)
        deduped = rag_dedupe(rag_results)
        cards = [format_rag_tour_card(r["metadata"]) for r in deduped]

    if not cards:
        return _error_result(f"No holiday packages found for {payload.city}.")

    cards = cards[: payload.limit]
    title = f"Holiday Packages in {payload.city}"

    structured = {
        "tours": cards,
        "title": title,
        "subtitle": f"{len(cards)} packages found",
        "totalResults": len(cards),
        "dataSource": data_source,
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
                        text=f"No visa information found for '{payload.country}'. Visit https://www.raynatours.com/visa for details.",
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

    lines.append(f"\nFor more details: https://www.raynatours.com/visa")

    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(lines))],
            isError=False,
        )
    )


async def _handle_ask_rayna(arguments: dict) -> types.ServerResult:
    """RAG-powered Q&A tool."""
    payload = AskRaynaInput.model_validate(arguments)
    question = payload.question

    if not HAS_RAG:
        return types.ServerResult(
            types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text="The knowledge base is currently unavailable. "
                         "Please try using show-tours or show-tour-detail instead, "
                         "or visit https://www.raynatours.com for help.",
                )],
                isError=False,
            )
        )

    results = rag_search_all(question, top_k=8)
    deduped = rag_dedupe(results)

    if not deduped or deduped[0]["score"] < 0.3:
        return types.ServerResult(
            types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=f"I couldn't find specific information about '{question}' in our knowledge base. "
                         f"Please visit https://www.raynatours.com or contact our team for help.",
                )],
                isError=False,
            )
        )

    lines = []
    for r in deduped[:5]:
        meta = r["metadata"]
        title = meta.get("title", "Info")
        if " | " in title:
            title = title.split(" | ")[0].strip()
        desc = meta.get("description", "") or meta.get("content", "")[:300]
        lines.append(f"**{title}**")
        if desc:
            lines.append(desc[:300])
        price = meta.get("price", "")
        if price:
            lines.append(f"Price: AED {price}")
        url = meta.get("url", "") or meta.get("urlPath", "")
        if url:
            lines.append(f"[View details]({url})")
        lines.append("")

    return types.ServerResult(
        types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(lines))],
            isError=False,
        )
    )


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
        elif tool_name == "ask-rayna":
            return await _handle_ask_rayna(arguments)
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
            "version": "1.0.0",
            "description": "Rayna Tours travel assistant — browse tours, holiday packages, compare activities, and get visa info across 50+ destinations.",
            "author": "Rayna Tours",
            "homepage": "https://www.raynatours.com",
            "support": "https://www.raynatours.com/contact-us",
            "pattern": "OpenAI Apps SDK",
            "protocol": "MCP (Streamable HTTP)",
            "ui": "React",
            "widgets": len(set(w.template_uri for w in widgets)),
            "tools": len(TOOL_SCHEMAS),
            "rag": HAS_RAG,
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
    rag_status = "Enabled (Pinecone)" if HAS_RAG else "Disabled (set OPENAI_API_KEY & PINECONE_API_KEY)"
    print(f"  RAG: {rag_status}")
    print(f"\n  For ChatGPT: http://localhost:{port}/mcp")
    print("  With ngrok: https://YOUR-URL.ngrok-free.app/mcp")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host="0.0.0.0", port=port)
