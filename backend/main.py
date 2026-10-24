"""Independent FastAPI backend for the Streamlit application."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.agent_service import run_agent
from backend.conversation_store import store
from backend.exceptions import AppError, ConversationNotFoundError, ExternalServiceError
from backend.optics_client import ingest_document
from backend.request_context import request_id
from backend.schemas import (
    ChatRequest,
    ChatResponse,
    ClientEventRequest,
    ConversationResponse,
    DocumentIngestResponse,
    HealthResponse,
)
from backend.logging_utils import get_logger


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(store.initialize)
    logger.info("Backend database initialized")
    yield


app = FastAPI(title="LangGraph MCP Agent Backend", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Critical boundary: assign one safe trace ID to every frontend request."""
    trace_id = request.headers.get("X-Request-ID", str(uuid4()))
    token = request_id.set(trace_id)
    started = perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        logger.info("HTTP request completed method=%s path=%s status=%d duration_ms=%d", request.method, request.url.path, response.status_code, (perf_counter() - started) * 1000)
        return response
    except Exception:
        logger.exception("HTTP request crashed method=%s path=%s", request.method, request.url.path)
        raise
    finally:
        request_id.reset(token)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, error: AppError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"code": error.code, "message": error.message})


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, error: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"code": "HTTP_ERROR", "message": str(error.detail)})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="langgraph-backend")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Critical frontend -> backend boundary. React posts the question here.
    try:
        conversation_id = request.conversation_id or await asyncio.to_thread(store.create)
        history = (
            await asyncio.to_thread(store.messages, conversation_id)
            if request.conversation_id
            else [message.model_dump() for message in request.history]
        )
        answer, artifacts = await run_agent(
            request.question,
            history,
            request.active_source_file,
        )
        await asyncio.to_thread(store.append_pair, conversation_id, request.question, answer, artifacts)
        return ChatResponse(answer=answer, artifacts=artifacts, conversation_id=conversation_id)
    except AppError:
        raise
    except Exception as error:
        logger.exception("Backend chat failed error_type=%s", type(error).__name__)
        raise ExternalServiceError("The agent could not complete the request. Check backend, MCP, and Optics services.") from error


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def conversation(conversation_id: str) -> ConversationResponse:
    messages = await asyncio.to_thread(store.messages, conversation_id)
    return ConversationResponse(id=conversation_id, messages=messages)


@app.post("/client-events", status_code=202)
async def client_event(event: ClientEventRequest) -> dict[str, str]:
    """Receive safe React diagnostics in the same backend trace log."""
    logger.info("Frontend event event=%s detail=%s", event.event, event.detail or "none")
    return {"status": "accepted"}


@app.post("/documents", response_model=DocumentIngestResponse)
async def ingest(file: UploadFile = File(...)) -> DocumentIngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    try:
        result = await asyncio.to_thread(
            ingest_document,
            file.filename,
            await file.read(),
            file.content_type,
        )
        return DocumentIngestResponse(
            filename=result.get("filename", file.filename),
            chunks_added=int(result.get("chunks_added", 0)),
        )
    except Exception as error:
        logger.exception("Backend document ingestion failed error_type=%s", type(error).__name__)
        raise ExternalServiceError("Document indexing failed. Check the Optics RAG service.") from error
