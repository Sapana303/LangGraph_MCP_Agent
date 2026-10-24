"""Typed HTTP contracts between the web UI, terminal client, and backend."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)
    artifacts: dict | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=50)
    active_source_file: str | None = Field(default=None, max_length=255)
    conversation_id: str | None = Field(default=None, max_length=64)


class ChatResponse(BaseModel):
    answer: str
    artifacts: dict | None = None
    conversation_id: str


class HealthResponse(BaseModel):
    status: str
    service: str


class DocumentIngestResponse(BaseModel):
    filename: str
    chunks_added: int


class ConversationResponse(BaseModel):
    id: str
    messages: list[ChatMessage]


class ClientEventRequest(BaseModel):
    """Small browser diagnostic event; never send prompts or document content."""

    event: Literal[
        "chat_completed",
        "chat_failed",
        "document_upload_completed",
        "document_upload_failed",
    ]
    detail: str | None = Field(default=None, pattern=r"^[A-Z0-9_]{1,64}$")
