# LangGraph MCP Assistant

An independently deployable agent system built with React, FastAPI, LangGraph, and Model Context Protocol (MCP). The backend LLM agent selects tools for safe filesystem access, current weather, web search, web scraping, and internal-document RAG.

The RAG capability deliberately reuses the existing `optics_rag` project. This repository does not create a second vector store, embedding pipeline, or retrieval strategy. Its RAG MCP server calls the Optics FastAPI `/query` endpoint, which retains Optics' Chroma, BM25, hybrid retrieval, and citation behavior.

## Architecture

```text
React UI (web/, port 5173 in development; port 8080 with Docker Compose by default)
  |
  | HTTP /chat
  v
FastAPI backend (backend/main.py, port 8001)
  |
  | LangGraph: START -> agent -> ToolNode -> agent -> END
  | MCP streamable HTTP: tool discovery + calls
  v
Single MCP tool service (mcp_service/main.py, port 8002)
  +-- filesystem, weather, web-search, RAG, scraper tools
  |
  v
Optics RAG FastAPI (separate project, port 8000)
  +-- Chroma + BM25 hybrid retrieval + citations/images
```

The UI displays data and calls the backend only. The backend owns LangGraph and discovers tool schemas from the MCP service. `tools_condition` routes only model-requested calls to the `ToolNode`, so there is no large `if`/`elif` intent router.

## Run with Docker Compose

Docker Compose is the recommended way to run the complete React UI, FastAPI backend, and MCP tool service. Install Docker Desktop on Windows or Docker Engine with the Compose plugin on Linux, then run these commands in PowerShell from the project folder:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` and set `GROQ_API_KEY` to your key. `TAVILY_API_KEY` is optional; without it, web search uses the DuckDuckGo fallback. Then start the services:

```powershell
docker compose up --build -d
```

Open **http://localhost:8080**. To follow service output or stop the containers:

```powershell
docker compose ps
docker compose logs -f
docker compose down
```

`docker compose down` preserves chat history in the `chat_data` volume. The services write `frontend.log`, `backend.log`, and `mcp-service.log` into the local `logs/` directory. Only the web UI is exposed on the host; the backend and MCP service communicate over the private Compose network.

### Connect Optics RAG

If your separate Optics RAG service is running on the same computer on port 8000, Compose routes its requests through `host.docker.internal`. Make sure Optics listens on an interface Docker can reach (for Uvicorn, use `--host 0.0.0.0 --port 8000`). If it runs at a different address, set `DOCKER_OPTICS_RAG_API_URL` in `.env`, for example `DOCKER_OPTICS_RAG_API_URL=http://host.docker.internal:8000`. The app can also run without Optics; chat, weather, web search, and scraping do not require it.

For an Oracle Cloud VM or another Linux host, use the same Compose command after creating `.env`. Set `APP_PORT=80` in `.env` if you want the app at `http://<public-ip>/`; otherwise it uses port 8080. Allow the chosen TCP port in the cloud network rules and host firewall. For Optics running on that VM, make its API reachable from Docker containers and set `DOCKER_OPTICS_RAG_API_URL` to the host address and port.

To update after pulling changes, run `docker compose up --build -d` again. Do not commit `.env`.

## Run services separately for development

Use Python 3.10 or later. Install the Python dependencies and create `.env` if needed:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Run the MCP service and backend in separate terminals (activate `.venv` in each terminal):

```powershell
uvicorn mcp_service.asgi:app --reload --port 8002
```

```powershell
uvicorn backend.main:app --reload --port 8001
```

The MCP endpoint is `http://127.0.0.1:8002/mcp`; the backend health endpoint is `http://127.0.0.1:8001/health`. Start the React development server in another terminal (Node.js LTS required):

```powershell
npm --prefix web install
npm --prefix web run dev
```

Open `http://localhost:5173`. To use RAG locally, also start your Optics project on port 8000 and set `OPTICS_RAG_API_URL` in `.env` if needed.

## Run the terminal client

```powershell
python -m backend.cli
```

The backend must already be running. This client uses the same `/chat` API as the UI.

The React sidebar supports PDF, DOCX, XLSX, Markdown, and text uploads. Selecting a file sends it through the backend to Optics RAG. After it succeeds, you can ask the agent questions about that document immediately.

Example requests:

- `List files in ./mcp_service/tools`
- `What is the weather in Bangalore?`
- `Search the web for LangGraph MCP integration`
- `What does the uploaded employee handbook say about paid leave?`
- `Read https://example.com and tell me the page title`
- `Search the web for the latest LangGraph release and scrape the official release page`

`mcp_service/main.py` is the one MCP server entry point. Reusable implementation for each capability remains in `mcp_service/tools/`.

## Tests

```powershell
pytest
```

The tests cover safe filesystem boundaries, invalid scraper input, and an unavailable RAG service. Tests are offline and do not consume credentials.

## Error handling and observability

All tools return structured `ok`/`error` responses instead of leaking tracebacks. The graph's `ToolNode` converts unexpected tool exceptions into tool results, allowing the LLM to explain the failure.

Logs are separated by service: `logs/frontend.log` receives safe React UI events, `logs/backend.log` records API and agent activity, and `logs/mcp-service.log` records MCP tool activity. Backend and web event logs use rotating JSON logs with a per-request `request_id`, so a browser event can be matched to its API request. To protect private data, logs record question length rather than question text, and never record API keys, `.env` values, document content, or complete URL query strings.

Chat history is stored in SQLite. In local development it uses `data/chat_history.db`; Docker Compose stores it in the persistent `chat_data` volume. Assistant artifact metadata, such as RAG citations and image references, is stored with the assistant reply so reopening the conversation keeps its sources visible.

The configured `GROQ_MODEL` is tried first. Set `GROQ_FALLBACK_MODELS` to a comma-separated list in `.env` to customize the fallback order.

## Known limitations

- The command-line agent needs a reachable Groq API and a configured key.
- Public web search can use DuckDuckGo without a key; Tavily is recommended for more reliable structured search results.
- RAG requires the Optics FastAPI service and an already ingested collection.
- The scraper cleans common boilerplate and can try Crawl4AI for JavaScript-rendered pages when `CRAWL4AI_ENABLED=true`. Crawl4AI is optional; after installing dependencies, follow its browser-install instructions before enabling it. It does not bypass authentication, paywalls, or robots restrictions.

## Viva notes

LangGraph controls stateful, conditional LLM workflows; MCP lets clients discover and call external tool servers through typed schemas. Here `backend/mcp_client.py` connects to one `mcp_service/main.py` server, and LangGraph coordinates the agent/tool loop. A new capability is added by implementing a safe helper in `mcp_service/tools/`, exposing it with `@mcp.tool()` in `mcp_service/main.py`, and letting the backend discover its schema.
