"""Terminal client for the independently running LangGraph backend."""

from __future__ import annotations

from frontend.api_client import BackendUnavailableError, ask_backend


def main() -> None:
    """Keep a simple terminal interface without duplicating backend logic."""
    print("LangGraph MCP Assistant. Type 'quit' to exit.")
    history: list[dict[str, str]] = []
    while True:
        question = input("You: ").strip()
        if question.lower() in {"quit", "exit"}:
            return
        if not question:
            continue
        try:
            answer, _ = ask_backend(question, history, active_source_file=None)
        except BackendUnavailableError:
            print("Assistant: Backend is unavailable. Start it with `uvicorn backend.main:app --reload --port 8001`.")
            continue
        print(f"Assistant: {answer}")
        history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ]
        )


if __name__ == "__main__":
    main()
