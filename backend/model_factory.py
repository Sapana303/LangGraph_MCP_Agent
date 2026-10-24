"""Groq model cascade with narrow retries for transient provider failures."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from backend.config import (
    GROQ_FALLBACK_MODELS,
    GROQ_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_ENABLED,
    OLLAMA_MODEL,
)
from backend.exceptions import ModelUnavailableError
from backend.logging_utils import get_logger


logger = get_logger(__name__)


def build_models(tools: list) -> list[tuple[str, object]]:
    """Build Groq models followed by an optional local Ollama fallback."""
    if LLM_PROVIDER == "ollama":
        return [
            (
                f"ollama/{OLLAMA_MODEL}",
                ChatOllama(
                    model=OLLAMA_MODEL,
                    base_url=OLLAMA_BASE_URL,
                    temperature=0,
                ).bind_tools(tools),
            )
        ]

    model_ids = tuple(dict.fromkeys((GROQ_MODEL, *GROQ_FALLBACK_MODELS)))
    models = [
        (model_id, ChatGroq(model=model_id, temperature=0, max_retries=0).bind_tools(tools))
        for model_id in model_ids
    ]
    if OLLAMA_ENABLED:
        models.append(
            (
                f"ollama/{OLLAMA_MODEL}",
                ChatOllama(
                    model=OLLAMA_MODEL,
                    base_url=OLLAMA_BASE_URL,
                    temperature=0,
                ).bind_tools(tools),
            )
        )
    return models


def _is_transient(error: Exception) -> bool:
    message = str(error).lower()
    return any(token in message for token in ("429", "rate limit", "timeout", "timed out", "503", "502", "connection"))


async def invoke_with_fallback(models: Sequence[tuple[str, object]], messages: list) -> object:
    """Try a model once, retry one transient failure, then move to a fallback model."""
    last_error: Exception | None = None
    for model_id, model in models:
        for attempt in range(2):
            try:
                logger.info("Model invocation started model=%s attempt=%d", model_id, attempt + 1)
                response = await model.ainvoke(messages)  # type: ignore[attr-defined]
                logger.info("Model invocation completed model=%s", model_id)
                return response
            except Exception as error:
                last_error = error
                retry = attempt == 0 and _is_transient(error)
                logger.warning(
                    "Model invocation failed model=%s attempt=%d retry=%s error_type=%s",
                    model_id, attempt + 1, retry, type(error).__name__,
                )
                if retry:
                    await asyncio.sleep(0.6)
                    continue
                break
    raise ModelUnavailableError("All configured language models are currently unavailable.", detail=str(last_error))
