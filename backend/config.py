"""Configuration owned by the FastAPI and LangGraph backend."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# Environment variables supplied by Docker or a hosting platform take precedence
# over the local .env file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8001").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
GROQ_FALLBACK_MODELS = tuple(
    model.strip()
    for model in os.getenv("GROQ_FALLBACK_MODELS", "qwen/qwen3-32b,llama-3.3-70b-versatile").split(",")
    if model.strip()
)
MAX_CHAT_HISTORY_MESSAGES = int(os.getenv("MAX_CHAT_HISTORY_MESSAGES", "12"))
OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8002/mcp").rstrip("/")
OPTICS_RAG_API_URL = os.getenv("OPTICS_RAG_API_URL", "http://127.0.0.1:8000").rstrip("/")
DATABASE_PATH = Path(os.getenv("CHAT_DATABASE_PATH", PROJECT_ROOT / "data" / "chat_history.db"))
