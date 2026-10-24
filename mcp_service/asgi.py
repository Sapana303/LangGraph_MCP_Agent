"""ASGI entry point for development reload and production hosting."""

from mcp_service.main import mcp


# Uvicorn serves this app and can reload it when main.py or tools/ changes.
app = mcp.streamable_http_app()
