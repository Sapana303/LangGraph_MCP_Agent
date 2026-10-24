"""Configuration owned by the Streamlit frontend."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://127.0.0.1:8001").rstrip("/")
