# Rayna Tours ChatGPT App SDK — Project Flow Document

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack](#2-tech-stack)
3. [Project Structure](#3-project-structure)
4. [Environment Setup](#4-environment-setup)
5. [Server Startup Flow](#5-server-startup-flow)
6. [MCP Protocol — How ChatGPT Communicates](#6-mcp-protocol--how-chatgpt-communicates)
7. [Tool-by-Tool Detailed Flow](#7-tool-by-tool-detailed-flow)
8. [RAG Engine — Knowledge Base & Vector Search](#8-rag-engine--knowledge-base--vector-search)
9. [Rayna API Client — Live Data Fetching](#9-rayna-api-client--live-data-fetching)
10. [React UI Widgets — Frontend Rendering](#10-react-ui-widgets--frontend-rendering)
11. [End-to-End Request Flow (Full Example)](#11-end-to-end-request-flow-full-example)
12. [Knowledge Base Ingestion](#12-knowledge-base-ingestion)
13. [Deployment](#13-deployment)
14. [File Reference](#14-file-reference)

---

## 1. Project Overview

This project is a **ChatGPT App SDK MCP Server** for **Rayna Tours**. It allows ChatGPT to:

- Search and display tour packages as interactive card grids
- Show detailed tour information with images, pricing, and booking links
- Compare multiple tours side-by-side
- Display holiday packages and visa information
- Answer general questions about Rayna Tours (FAQs, policies, company info)

When a user asks ChatGPT about tours, holidays, or visas, ChatGPT calls this server's **MCP tools**, and the server responds with:
- **Text summaries** (displayed in the chat)
- **React UI widgets** (rendered inline as interactive cards inside ChatGPT)

### What is MCP?

**Model Context Protocol (MCP)** is a standardized protocol that allows AI models (like ChatGPT) to call external tools and display rich UI. Think of it as an API that ChatGPT uses to "call functions" on your server and render the results as widgets.

---

## 2. Tech Stack

### Backend (Python)
| Technology | Purpose |
|------------|---------|
| **Python 3.11** | Runtime language |
| **FastMCP** (`fastmcp`) | MCP server framework — handles protocol, tool registration |
| **Uvicorn** | ASGI HTTP server |
| **Starlette** | HTTP middleware (CORS) |
| **OpenAI SDK** | Generates text embeddings for RAG search |
| **Pinecone** | Vector database for semantic search |
| **aiohttp** | Async HTTP client for calling Rayna's API |
| **cachetools** | TTL caching for city ID lookups |
| **Pydantic** | Input validation schemas for tool parameters |
| **python-dotenv** | Loads `.env` file |

### Frontend (React/TypeScript)
| Technology | Purpose |
|------------|---------|
| **React 18** | UI rendering framework |
| **TypeScript** | Type-safe JavaScript |
| **esbuild** | Fast bundler (compiles to ESM) |

### External Services
| Service | Purpose |
|---------|---------|
| **Rayna Tours API** | Live tour/holiday/visa data |
| **Pinecone** | Vector database for RAG |
| **OpenAI API** | Text embeddings (`text-embedding-ada-002`) |
| **ChatGPT** | The AI client that calls this server |

---

## 3. Project Structure

```
raynachatgptsdk-app/
│
├── server.py                  # MAIN SERVER: MCP tools, HTTP routes, widget delivery
├── rag_engine.py              # RAG engine: embeddings + Pinecone vector search
├── rayna_utils.py             # API client, data formatting, helpers
├── ingest.py                  # Script to load knowledge base into Pinecone
│
├── knowledge_base/            # Static knowledge documents
│   ├── custom.json            #   Company info (about, destinations, contact)
│   ├── faqs.json              #   FAQ entries (cancellation, booking, etc.)
│   └── policies.json          #   Policy docs (health, insurance, accessibility)
│
├── web/                       # React UI widgets
│   ├── package.json           #   Dependencies + build scripts
│   ├── tsconfig.json          #   TypeScript config
│   ├── src/
│   │   ├── types.ts           #     TypeScript interfaces
│   │   ├── hooks.ts           #     React hooks for OpenAI SDK
│   │   ├── TourListComponent.tsx      #   Tour card grid widget
│   │   ├── TourDetailComponent.tsx    #   Tour detail page widget
│   │   └── TourCompareComponent.tsx   #   Tour comparison table widget
│   └── dist/                  #   Built JS bundles (output)
│       ├── tour-list.js
│       ├── tour-detail.js
│       └── tour-compare.js
│
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (API keys)
├── .env.example               # Template for .env
├── Dockerfile                 # Docker build (Python + Node)
├── railway.json               # Railway.app deployment config
├── START.sh                   # Shell script: build React + start server
└── README.md                  # Quick start guide
```

---

## 4. Environment Setup

### Required Environment Variables (`.env`)

```env
RAYNA_API_BASE_URL=https://earnest-panda-e8edbd.netlify.app/api    # Rayna Tours API proxy
OPENAI_API_KEY=sk-proj-...                                          # For generating embeddings (RAG)
PINECONE_API_KEY=pcsk_...                                           # For vector database search
PINECONE_INDEX_NAME=raynatours-test1                                # Pinecone index name
PORT=8000                                                           # Server port (default: 8000)
OPENAI_VERIFICATION_TOKEN=...                                       # ChatGPT app verification
```

### What happens if keys are missing?
- If `OPENAI_API_KEY` or `PINECONE_API_KEY` are missing → **RAG is disabled** (`HAS_RAG = False`)
- The `ask-rayna` tool is hidden from the tool list
- `show-tours`, `show-tour-detail`, and `show-holiday-packages` work via **live API only** (no fallback to vector search)

---

## 5. Server Startup Flow

When you run `uv run python server.py`, here's what happens step by step:

```
Step 1: Load environment variables
    └── python-dotenv reads .env file

Step 2: Import RAG engine (optional)
    ├── Try importing rag_engine.py
    ├── If OpenAI + Pinecone keys exist → HAS_RAG = True
    └── If keys missing or import fails → HAS_RAG = False (graceful degradation)

Step 3: Load React bundles from web/dist/
    ├── Read tour-list.js, tour-detail.js, tour-compare.js into memory
    ├── If files exist → HAS_UI = True
    └── If files missing → HAS_UI = False (prints warning)

Step 4: Define 3 widget definitions
    ├── WIDGET_TOUR_LIST  → "rayna-tour-list.html"
    ├── WIDGET_TOUR_DETAIL → "rayna-tour-detail.html"
    └── WIDGET_TOUR_COMPARE → "rayna-tour-compare.html"

Step 5: Create FastMCP server instance
    └── FastMCP(name="rayna-tours", sse_path="/mcp", stateless_http=True)

Step 6: Register MCP protocol handlers
    ├── list_tools      → Returns available tool definitions
    ├── list_resources   → Returns widget resource definitions
    ├── read_resource    → Returns widget HTML content
    └── call_tool        → Routes to appropriate tool handler

Step 7: Create Starlette ASGI app
    ├── Add CORS middleware (allow all origins)
    ├── Add /health endpoint
    ├── Add /info endpoint
    └── Add /.well-known/openai-apps-challenge endpoint

Step 8: Start Uvicorn server
    └── uvicorn.run(app, host="0.0.0.0", port=8000)
```

### HTTP Endpoints Available After Startup

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/mcp` | POST | MCP protocol (all tool calls go here) |
| `/health` | GET | Health check → `{"status": "healthy"}` |
| `/info` | GET | Server metadata (tools count, RAG status) |
| `/.well-known/openai-apps-challenge` | GET | OpenAI verification token |

---

## 6. MCP Protocol — How ChatGPT Communicates

### The Communication Flow

```
┌──────────┐       POST /mcp        ┌──────────────┐
│          │ ───────────────────────→│              │
│  ChatGPT │  JSON-RPC request       │  MCP Server  │
│          │ ←───────────────────────│  (server.py) │
│          │  JSON-RPC response      │              │
└──────────┘  (text + widget data)   └──────────────┘
```

### MCP Request Types

ChatGPT sends JSON-RPC style requests to `/mcp`:

| Request | Handler Function | What It Does |
|---------|-----------------|--------------|
| `tools/list` | `_list_tools()` | Returns list of available tools + their input schemas |
| `resources/list` | `_list_resources()` | Returns list of widget templates |
| `resources/read` | `_handle_read_resource()` | Returns the HTML content of a widget |
| `tools/call` | `_call_tool_request()` | Executes a tool and returns results |

### Tool Response Structure

Every tool response contains:

```
ServerResult
├── CallToolResult
│   ├── content: [TextContent]          # Plain text summary for the chat
│   ├── structuredContent: {...}         # JSON data for the React widget
│   └── isError: false
└── _meta: {
        "openai.com/widget": {           # Embedded HTML widget
            html: "<div>...</div>"
        },
        "openai/outputTemplate": "...",  # Widget template URI
        "openai/toolInvocation/invoking": "Searching tours...",
        "openai/toolInvocation/invoked": "Showing tour list"
    }
```

---

## 7. Tool-by-Tool Detailed Flow

### Tool 1: `show-tours`

**Purpose:** Search and display tour packages for a city.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `city` | string | Yes | City name (e.g., "Dubai") |
| `tour_name` | string | No | Specific tour to search for |

**Flow:**
```
1. Receive: { city: "Dubai", tour_name: "desert safari" }
        │
2. Resolve city name → city ID
   │   └── RaynaApiClient.resolve_city_id("Dubai") → city_id = 1
   │       (calls GET /available-cities, cached 5 min)
   │
3. Fetch products from live API
   │   └── GET /city/products?cityId=1&limit=200
   │       Returns raw product list
   │
4. Format each product → standard TourCard
   │   └── format_tour_card(raw_product, "Dubai")
   │       Extracts: name, price, image, URL, duration, rating, highlights
   │
5. Filter by tour_name (if provided)
   │   ├── Qualifier-aware filtering (rejects "morning" if user said "evening")
   │   ├── Score: exact match (3) > all words (2) > category match (1)
   │   └── Sort by score descending, take top 6
   │
6. If no results → Fallback to RAG (Pinecone)
   │   └── rag_search_tours("desert safari in Dubai")
   │       → Embed query → Pinecone search → Dedupe → Format
   │
7. Build response
   │   ├── Text: "Found 4 tours: 1. Evening Desert Safari (AED 85)..."
   │   ├── Structured: { tours: [...], title: "Desert Safari Tours in Dubai" }
   │   └── Widget: TourListComponent HTML with embedded JS bundle
   │
8. Return ServerResult → ChatGPT renders the card grid
```

---

### Tool 2: `show-tour-detail`

**Purpose:** Show detailed information about a specific tour.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tour_url` | string | No | Direct URL of the tour on raynatours.com |
| `tour_name` | string | No | Tour name to search for |

**Flow:**
```
1. If tour_url provided:
   │   └── GET /product-details?url=<tour_url>
   │       Returns full details (description, itinerary, inclusions, etc.)
   │
2. If tour_name provided (no URL):
   │   └── RAG search → Find best matching tour → Get URL → Fetch details
   │
3. Format into TourDetailOutput
   │   ├── Hero image, price, duration, rating
   │   ├── Description, highlights, inclusions/exclusions
   │   └── Booking URL
   │
4. Return ServerResult with TourDetailComponent widget
```

---

### Tool 3: `compare-tours`

**Purpose:** Compare 2+ tours side-by-side.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tour_names` | string[] | Yes | List of tour names to compare |

**Flow:**
```
1. For each tour name → RAG search in Pinecone
   │
2. Deduplicate results
   │
3. Format comparison data
   │   ├── Thumbnail cards per tour
   │   └── Comparison table: Price, Rating, Duration, Category, Location, R-Points
   │
4. Return ServerResult with TourCompareComponent widget
```

---

### Tool 4: `show-holiday-packages`

**Purpose:** Display holiday packages for a destination.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `destination` | string | Yes | Destination name |

**Flow:**
```
1. Resolve destination → city IDs (may resolve country → multiple cities)
   │   └── Uses REGION_TO_CITIES mapping for countries/regions
   │
2. Fetch holiday packages
   │   └── GET /city/holiday?cityId=<id> for each city
   │
3. Format as TourCards (reuses same format as tours)
   │
4. Fallback to RAG if no API results
   │
5. Return ServerResult with TourListComponent widget (reused)
```

---

### Tool 5: `get-visa-info`

**Purpose:** Get visa requirements for a country.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `country` | string | Yes | Country name |

**Flow:**
```
1. GET /visas?country=<country>
   │
2. Format visa information as text
   │   ├── Requirements, processing time, fees
   │   └── Document checklist
   │
3. Return ServerResult with TEXT ONLY (no widget)
```

---

### Tool 6: `ask-rayna` (RAG-only)

**Purpose:** Answer general questions about Rayna Tours using the knowledge base.

**Input Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `question` | string | Yes | User's question |

**Flow:**
```
1. Semantic search in Pinecone
   │   └── rag_search_all(question) → searches across all document types
   │
2. Return matching knowledge base entries as text
   │   ├── FAQs, policies, company info
   │   └── Tour/blog snippets if relevant
   │
3. Return ServerResult with TEXT ONLY (no widget)
```

**Note:** This tool is only available when `HAS_RAG = True` (both OpenAI and Pinecone keys configured).

---

## 8. RAG Engine — Knowledge Base & Vector Search

### File: `rag_engine.py`

### What is RAG?

**RAG (Retrieval-Augmented Generation)** enhances AI responses by searching a knowledge base for relevant information before answering. Instead of relying only on the AI's training data, it pulls real, specific information from your own documents.

### How It Works

```
┌──────────┐    embed query    ┌──────────────┐    search     ┌──────────┐
│  Query   │ ────────────────→ │  OpenAI API  │ ──────────→   │ Pinecone │
│ "cancel  │    (1536-dim      │  Embeddings  │  similarity   │  Vector  │
│  policy" │     vector)       │  ada-002     │   search      │    DB    │
└──────────┘                   └──────────────┘               └──────────┘
                                                                    │
                                                              Top K matches
                                                                    │
                                                                    ▼
                                                              ┌──────────┐
                                                              │ Results  │
                                                              │ (ranked) │
                                                              └──────────┘
```

### Search Functions

| Function | Purpose | Filter |
|----------|---------|--------|
| `search(query, top_k, filter_dict)` | General search with optional filter | Custom |
| `search_tours(query, top_k=6)` | Search only tour documents | `{"pageType": "tour"}` |
| `search_all(query, top_k=5)` | Search across all document types | None |
| `dedupe_by_parent(results)` | Keep best chunk per parent document | N/A |

### Vector Document Metadata Schema

Each document stored in Pinecone has this metadata:

```json
{
    "title": "Evening Desert Safari",
    "description": "Experience the magic of Arabian desert...",
    "content": "Full text content of the document...",
    "pageType": "tour",           // tour | faq | policy | blog
    "source": "https://raynatours.com/...",
    "mainImage": "https://...",
    "imageUrls": ["https://..."],
    "location": "Dubai",
    "destination": "UAE",
    "itinerary": "...",
    "duration": "6 hours",
    "price": "85",
    "highlights": ["Dune bashing", "BBQ dinner"],
    "chunkIndex": 0,              // For long documents split into chunks
    "totalChunks": 1,
    "parentDocumentId": "tour-123"
}
```

---

## 9. Rayna API Client — Live Data Fetching

### File: `rayna_utils.py`

### API Base URL
```
https://earnest-panda-e8edbd.netlify.app/api
```

### API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/available-cities?productType=tour` | GET | List all cities with tours |
| `/city/products?cityId=1&limit=20` | GET | Get tour products for a city |
| `/city/holiday?cityId=1` | GET | Get holiday packages for a city |
| `/product-details?url=...` | GET | Get full details of a specific tour |
| `/visas?country=...` | GET | Get visa information |

### City Resolution Flow

```
User says "Dubai"
    │
    ├── Exact match? → "Dubai" == "Dubai" ✓ → city_id = 1
    │
    ├── If no exact match → Fuzzy match
    │   └── "abu dhabi" matches "Abu Dhabi" → city_id = 2
    │
    └── If country/region name → REGION_TO_CITIES mapping
        └── "UAE" → ["Dubai", "Abu Dhabi", "Sharjah", "Ras Al Khaimah"]
            → Resolves each city → returns multiple city_ids
```

### Tour Card Formatting

The `format_tour_card()` function normalizes raw API data into a standard shape:

```json
{
    "name": "Evening Desert Safari with BBQ Dinner",
    "price": 85,
    "currency": "AED",
    "image": "https://cdn.raynatours.com/...",
    "url": "https://www.raynatours.com/evening-desert-safari",
    "duration": "6 hours",
    "rating": 4.8,
    "reviewCount": 1250,
    "description": "Experience the thrill of dune bashing...",
    "highlights": ["Dune Bashing", "BBQ Dinner", "Camel Ride"],
    "category": "Desert Safari",
    "location": "Dubai",
    "discount": 20,
    "rpoints": 170
}
```

### Caching

- City ID lookups are cached using `TTLCache(maxsize=32, ttl=300)` (5 minutes)
- Prevents repeated API calls for the same city within a session

---

## 10. React UI Widgets — Frontend Rendering

### How Widgets Are Delivered to ChatGPT

```
1. At server startup:
   │   Read tour-list.js, tour-detail.js, tour-compare.js into memory
   │
2. When a tool is called (e.g., show-tours):
   │   Build HTML string = <div id="root"> + <script>{JS_BUNDLE}</script>
   │   Attach HTML as widget metadata in the MCP response
   │
3. ChatGPT receives the response:
   │   Renders the HTML in a sandboxed iframe
   │   Injects window.openai with:
   │     - toolOutput (the structured JSON data)
   │     - theme ("light" or "dark")
   │
4. React widget mounts:
       Reads window.openai.toolOutput → renders the UI
```

### Widget Components

#### TourListComponent (`TourListComponent.tsx`)
- **Renders:** Horizontally scrollable card grid (260-280px wide cards)
- **Each card shows:** Tour image, discount badge, location, rating, title, duration, price, highlights, "Book on Rayna Tours" button
- **Features:** Favorites (heart toggle), scroll-snap, dark/light theme
- **Data source:** `TourListOutput` → `{ tours: TourCard[], title: string }`

#### TourDetailComponent (`TourDetailComponent.tsx`)
- **Renders:** Full tour detail page
- **Shows:** Hero image, price card, stats grid (duration/rating/R-Points), description, highlights, inclusions/exclusions, "Book Now" CTA
- **Data source:** `TourDetailOutput` → full tour object

#### TourCompareComponent (`TourCompareComponent.tsx`)
- **Renders:** Comparison grid + detailed table
- **Shows:** Thumbnail cards per tour + table with Price, Rating, Duration, Category, Location, R-Points
- **Highlights:** "Better" values in the comparison
- **Data source:** `TourComparisonOutput` → `{ tours: TourCard[] }`

### React Hooks (`hooks.ts`)

| Hook | Purpose |
|------|---------|
| `useToolOutput()` | Reads structured JSON data from `window.openai.toolOutput` |
| `useTheme()` | Reads current theme ("light" / "dark") |
| `useWidgetState(default)` | Persists widget state (e.g., favorites) via `window.openai.setWidgetState()` |
| `useOpenAiGlobal(key)` | Low-level: subscribes to OpenAI SDK global value changes |

### Booking Action

When a user clicks "Book on Rayna Tours":
```javascript
window.openai.openExternal({ href: tour.url })
// Falls back to window.open(tour.url) if openExternal unavailable
```

---

## 11. End-to-End Request Flow (Full Example)

### Scenario: User asks "Show me desert safari tours in Dubai"

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         COMPLETE REQUEST FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

Step 1: USER → ChatGPT
    User types: "Show me desert safari tours in Dubai"

Step 2: ChatGPT → MCP Server
    ChatGPT recognizes this needs the show-tours tool
    Sends POST /mcp:
    {
        "method": "tools/call",
        "params": {
            "name": "show-tours",
            "arguments": { "city": "Dubai", "tour_name": "desert safari" }
        }
    }

Step 3: MCP Server → _handle_show_tours()
    ├── Parse input: city="Dubai", tour_name="desert safari"
    └── Create aiohttp session

Step 4: Resolve City ID
    ├── GET https://earnest-panda.netlify.app/api/available-cities?productType=tour
    ├── Find "Dubai" in response → city_id = 1
    └── Cache result for 5 minutes

Step 5: Fetch Products
    ├── GET /city/products?cityId=1&limit=200
    └── Returns ~200 raw tour products

Step 6: Format Products
    └── For each raw product → format_tour_card(raw, "Dubai")
        → Standardized TourCard objects

Step 7: Filter by "desert safari"
    ├── Score each tour against "desert safari"
    │   ├── "Evening Desert Safari" → exact match → score 3
    │   ├── "Morning Desert Safari" → exact match → score 3
    │   ├── "Premium Desert Safari" → exact match → score 3
    │   └── "Dubai City Tour" → no match → score 0
    ├── Sort by score descending
    └── Take top 6 matches

Step 8: Build Text Summary
    "Found 4 desert safari tours in Dubai:
     1. Evening Desert Safari with BBQ Dinner — AED 85
     2. Premium Red Dune Desert Safari — AED 120
     3. Morning Desert Safari — AED 75
     4. VIP Desert Safari Experience — AED 250"

Step 9: Build Widget HTML
    ├── <div id="rayna-tour-list">
    ├── <script type="module">
    │       // Entire tour-list.js bundle embedded here
    │   </script>
    └── </div>

Step 10: Build Structured Content
    {
        "tours": [
            { "name": "Evening Desert Safari...", "price": 85, ... },
            { "name": "Premium Red Dune...", "price": 120, ... },
            ...
        ],
        "title": "Desert Safari Tours in Dubai",
        "subtitle": "4 tours found"
    }

Step 11: MCP Server → ChatGPT
    ServerResult {
        content: [TextContent(text_summary)],
        structuredContent: { tours, title, subtitle },
        _meta: {
            "openai.com/widget": { html: widget_html },
            "openai/outputTemplate": "ui://widget/rayna-tour-list.html"
        }
    }

Step 12: ChatGPT → USER
    ├── Displays text summary in chat
    └── Renders React widget (TourListComponent) inline:
        ┌─────────────────────────────────────────────────┐
        │  ┌─────────┐ ┌─────────┐ ┌─────────┐          │
        │  │ 🏜️      │ │ 🏜️      │ │ 🏜️      │  ← ──→  │
        │  │ Evening  │ │ Premium │ │ Morning │          │
        │  │ Desert   │ │ Red Dune│ │ Desert  │          │
        │  │ Safari   │ │ Safari  │ │ Safari  │          │
        │  │          │ │         │ │         │          │
        │  │ AED 85   │ │ AED 120 │ │ AED 75  │          │
        │  │ [Book]   │ │ [Book]  │ │ [Book]  │          │
        │  └─────────┘ └─────────┘ └─────────┘          │
        └─────────────────────────────────────────────────┘

Step 13: USER Clicks "Book on Rayna Tours"
    └── window.openai.openExternal({ href: "https://raynatours.com/..." })
        → Opens Rayna Tours website in browser
```

---

## 12. Knowledge Base Ingestion

### File: `ingest.py`

### Purpose
One-time script to load knowledge base documents into Pinecone for RAG search.

### Knowledge Base Files

#### `custom.json` — Company Information (3 documents)
- **About Rayna Tours:** Company overview, founding year, services
- **Popular Destinations:** List of all destinations served
- **Contact Information:** Email, phone, office locations

#### `faqs.json` — Frequently Asked Questions (10 documents)
- Cancellation & refund policy
- How to book a tour
- Payment methods accepted
- Hotel pickup service
- Children's pricing policy
- Dress code guidelines
- Group discount availability
- R-Points loyalty program
- Best time to visit Dubai
- Best time to visit Thailand

#### `policies.json` — Company Policies (3 documents)
- Health & safety policies
- Travel insurance information
- Accessibility accommodations

### Ingestion Flow
```
1. Read JSON files from knowledge_base/
2. For each document → generate embedding via OpenAI
3. Upsert vectors into Pinecone index "raynatours-test1"

Note: Tour data is NOT ingested — it comes live from the Rayna API.
      Only FAQs, policies, and company info are stored in Pinecone.
```

---

## 13. Deployment

### Local Development

```bash
# 1. Build React UI widgets
cd web && npm install && npm run build && cd ..

# 2. Install Python dependencies
uv sync

# 3. Set up .env file with API keys

# 4. Start the server
uv run python server.py
# Server runs at http://localhost:8000

# 5. Expose via ngrok for ChatGPT to reach
ngrok http 8000

# 6. In ChatGPT settings, add MCP server:
#    URL: https://YOUR-URL.ngrok-free.app/mcp
```

### Docker Deployment

```dockerfile
# Dockerfile summary:
FROM python:3.11-slim
    → Install Node.js 20
    → Install Python dependencies (requirements.txt)
    → Build React widgets (npm install && npm run build)
    → Copy source files
    → Run: uvicorn server:app --host 0.0.0.0 --port $PORT
```

### Railway Deployment

```json
// railway.json
{
    "build": { "builder": "DOCKERFILE" },
    "deploy": {
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
    }
}
```

Deploy steps:
1. Push to GitHub
2. Connect Railway to your repo
3. Set environment variables in Railway dashboard
4. Railway auto-builds and deploys using Dockerfile

---

## 14. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `server.py` | ~600 | Main server: MCP tools, handlers, widget delivery, HTTP routes |
| `rag_engine.py` | ~150 | RAG: OpenAI embeddings + Pinecone vector search |
| `rayna_utils.py` | ~500 | API client, card formatting, city resolution, data helpers |
| `ingest.py` | ~50 | Knowledge base → Pinecone ingestion script |
| `web/src/TourListComponent.tsx` | ~400 | Tour card grid React widget |
| `web/src/TourDetailComponent.tsx` | ~300 | Tour detail page React widget |
| `web/src/TourCompareComponent.tsx` | ~350 | Tour comparison table React widget |
| `web/src/hooks.ts` | ~80 | React hooks for OpenAI SDK integration |
| `web/src/types.ts` | ~60 | TypeScript interfaces |
| `knowledge_base/custom.json` | ~50 | Company info documents |
| `knowledge_base/faqs.json` | ~100 | FAQ documents |
| `knowledge_base/policies.json` | ~50 | Policy documents |

---

## Architecture Diagram

```
                            ┌─────────────────┐
                            │     ChatGPT     │
                            │   (AI Client)   │
                            └────────┬────────┘
                                     │
                              POST /mcp
                           (MCP Protocol)
                                     │
                            ┌────────▼────────┐
                            │   server.py     │
                            │   (FastMCP)     │
                            │                 │
                            │  6 MCP Tools    │
                            │  3 Widgets      │
                            └──┬─────┬────┬───┘
                               │     │    │
                 ┌─────────────┘     │    └──────────────┐
                 │                   │                   │
        ┌────────▼────────┐  ┌──────▼──────┐   ┌───────▼───────┐
        │  rayna_utils.py │  │rag_engine.py│   │   web/dist/   │
        │  (API Client)   │  │ (RAG Engine) │   │ (React Bundles│
        └────────┬────────┘  └──┬───────┬──┘   │  embedded in  │
                 │              │       │       │  responses)   │
        ┌────────▼────────┐ ┌──▼───┐ ┌─▼────┐ └───────────────┘
        │  Rayna Tours    │ │OpenAI│ │Pinecone
        │  API (Netlify)  │ │  API │ │Vector │
        │  Live data      │ │Embed │ │  DB   │
        └─────────────────┘ └──────┘ └───────┘
```

---

*Document generated for the raynachatgptsdk-app project.*
