"""The explicit LangGraph agent loop: START -> agent -> tools -> agent -> END."""

from __future__ import annotations

from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from backend.logging_utils import get_logger
from backend.model_factory import build_models, invoke_with_fallback

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a helpful assistant with MCP tools. Choose tools from intent, not keyword matching.

Tool routing guide:
- list_files: inspect the LangGraph_MCP_Agent project filesystem. It can list directories and files under the project root, including backend, frontend, mcp_service, data, logs, tests, and web. Use it for filesystem discovery only; it does not read file contents. Use recursive=true when the user asks to inspect nested folders.
- weather: current weather for a named location.
- web_search: discover public, current, or external information from a topic without a known URL.
- rag_search: answer from the user's indexed internal/uploaded documents and include its source information.
- scrape_page: read a specific URL the user provided, or a URL chosen from web_search results.
- match_resumes: compare many resumes in a folder against a job description, rank the best candidates, and show missing skills or improvement suggestions.

The uploaded knowledge base is an Optics technical document collection. Prefer rag_search before giving a generic
definition for technical, engineering, optics, materials, or document-specific terms that could reasonably exist in
that collection, such as attenuation, cladding, fibre, lens, coating, refractive index, or specifications. Also use
rag_search when the user asks for citations, sources, document images, or an answer based on uploaded content. If RAG
returns sources, ground the answer in its result and include a short ``Sources`` list using only the returned source
metadata. Do not invent citations. Do not use RAG for everyday greetings or clearly general questions unrelated to
the technical collection. When the user explicitly names an uploaded PDF, call rag_search and pass that exact name as
``source_file``; do not use list_files to decide whether an Optics-indexed document exists. When rag_search reports
``retrieval_found: false``, clearly say that the indexed document did not contain a relevant match and do not display
or invent sources. When rag_search reports ``image_available: true``, do not search the local filesystem or
the public web for another image. Finish the grounded answer and citations; the UI automatically displays Optics'
related image outside the model conversation. If it reports no image, say that no related image was retrieved rather
than making extra image-search calls, unless the user explicitly asks for a public-web image.

Response formatting rules:

- Always give answers in clean, readable Markdown.
- Use a clear heading for the main topic when appropriate.
- Use short paragraphs instead of large blocks of text.
- Use bullet points for lists.
- Use numbered lists for steps or procedures.
- Use Markdown tables only when they genuinely improve readability.
- Use **bold** for important terms, not for entire paragraphs.
- Do not output raw Markdown syntax as escaped text.
- Do not surround the entire answer with code fences unless the user asks for code.
- For technical explanations, prefer:
  1. Short explanation
  2. Key points
  3. Example
  4. Practical notes
- Keep answers natural and professional.
- Do not add unnecessary separators such as `---` unless they improve readability.
- Do not include a "Sources" section unless RAG or web tools actually returned sources.
- When sources are available from RAG, put them at the end under a short "Sources" heading.

For multi-step questions, call tools in the needed sequence, for example web_search followed by scrape_page. Never
claim a tool succeeded when it returned an error; explain the issue clearly."""


class AgentState(MessagesState):
    """Graph state stores the full conversation as append-only LangChain messages."""


def build_graph(tools: list, active_source_file: str | None = None) -> StateGraph:
    models = build_models(tools)
    tool_node = ToolNode(tools, handle_tool_errors=True)
    scoped_prompt = SYSTEM_PROMPT
    if active_source_file:
        scoped_prompt += (
            f"\n\nThe user selected `{active_source_file}` as the active uploaded document. "
            "For questions about internal document content, use rag_search and pass this exact value "
            "as source_file. Do not apply this document scope to weather, web, or normal conversation."
        )

    async def agent(state: AgentState) -> dict:
        previous: BaseMessage | None = state["messages"][-1] if state["messages"] else None
        if getattr(previous, "type", None) == "tool":
            logger.info("Tool completed: %s", getattr(previous, "name", "unknown"))
        logger.info("Calling configured model cascade message_count=%d", len(state["messages"]))
        response = await invoke_with_fallback(models, [SystemMessage(content=scoped_prompt), *state["messages"]])
        logger.info("Model completed requested_tools=%d", len(getattr(response, "tool_calls", [])))
        return {"messages": [response]}

    async def logged_tools(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        for call in getattr(last_message, "tool_calls", []):
            if call["name"] == "rag_search" and active_source_file:
                call["args"]["source_file"] = active_source_file
            arguments = call.get("args", {})
            logger.info(
                "Selected tool=%s argument_keys=%s query_chars=%d source_file=%s",
                call["name"],
                sorted(arguments),
                len(str(arguments.get("query", ""))),
                arguments.get("source_file", "none"),
            )
        return await tool_node.ainvoke(state)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", logged_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()
