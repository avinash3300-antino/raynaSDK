# Rayna Tours - ChatGPT App SDK

A ChatGPT App SDK project that renders beautiful tour cards directly inside ChatGPT conversations. Built with Python (FastMCP) + React/TypeScript UI widgets.

## Quick Start

```bash
# 1. Build React UI
cd web && npm install && npm run build && cd ..

# 2. Install Python deps
uv sync

# 3. Start server
uv run python server.py
```

Server runs on `http://localhost:8000`

## Connect to ChatGPT

1. Start ngrok: `ngrok http 8000`
2. In ChatGPT settings, add MCP server with URL: `https://YOUR-URL.ngrok-free.app/mcp`

## Tools

| Tool | Description | Widget |
|------|-------------|--------|
| `show-tours` | Search & display tour cards | Tour card grid |
| `show-tour-detail` | Detailed tour view | Tour detail page |
| `compare-tours` | Side-by-side comparison | Comparison table |
| `show-holiday-packages` | Holiday package cards | Tour card grid |
| `get-visa-info` | Visa requirements | Text only |

## Endpoints

- `/mcp` — MCP protocol (Streamable HTTP)
- `/health` — Health check
- `/info` — Server info
