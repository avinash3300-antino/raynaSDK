"""Vercel serverless entry point — exposes the Starlette ASGI app."""
import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app  # noqa: E402
