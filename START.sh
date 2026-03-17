#!/bin/bash
cd "$(dirname "$0")"
echo "============================================================"
echo "  Rayna Tours MCP Server - Quick Start"
echo "============================================================"

# Build React UI if not already built
if [ ! -f "web/dist/tour-list.js" ]; then
    echo ""
    echo "Building React UI components..."
    cd web
    npm install
    npm run build
    cd ..
    echo "React UI built successfully!"
fi

echo ""

if [ "$1" == "--stdio" ] || [ "$1" == "--inspector" ]; then
    echo "Starting with MCP Inspector (STDIO mode)..."
    npx @modelcontextprotocol/inspector uv run python server.py --stdio
else
    echo "Starting Rayna Tours MCP Server (Streamable HTTP)..."
    uv run python server.py
fi
