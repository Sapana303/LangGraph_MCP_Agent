"""Configuration owned by the independent MCP tool service."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

FILESYSTEM_ROOT = (PROJECT_ROOT / os.getenv("FILESYSTEM_ROOT", ".")).resolve()
OPTICS_RAG_API_URL = os.getenv("OPTICS_RAG_API_URL", "http://127.0.0.1:8000").rstrip("/")
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8002"))
