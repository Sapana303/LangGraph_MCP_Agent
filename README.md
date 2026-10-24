# LangGraph MCP Assistant

An independently deployable agent system built with React, FastAPI, LangGraph, and Model Context Protocol (MCP). The backend LLM agent selects tools for safe filesystem access, current weather, web search, web scraping, and internal-document RAG.

The RAG capability deliberately reuses the existing `optics_rag` project. This repository does not create a second vector store, embedding pipeline, or retrieval strategy. Its RAG MCP server calls the Optics FastAPI `/query` endpoint, which retains Optics' Chroma, BM25, hybrid retrieval, and citation behavior.

## Architecture

```text
React UI (web/, port 5173)
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

## Setup

Use Python 3.10 or later. From this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env`. `TAVILY_API_KEY` is optional: when it is configured, web search uses Tavily; otherwise it uses a public DuckDuckGo HTML fallback. Weather uses Open-Meteo's public API and does not need a key. Never commit `.env`.

## Start Services

Run each process in a separate terminal. They can be changed and restarted independently during development.

### 1. Optics RAG

```powershell
cd C:\Users\sapana.kumari\Downloads\optics_rag\optics_rag
.\venv\Scripts\Activate.ps1
uvicorn api.main:app --reload --port 8000
```

### 2. MCP Tool Service

```powershell
cd C:\Users\sapana.kumari\Downloads\LangGraph_MCP_Agent
.\.venv\Scripts\Activate.ps1
uvicorn mcp_service.asgi:app --reload --port 8002
```

It exposes all five tools at `http://127.0.0.1:8002/mcp`.

### 3. LangGraph Backend

```powershell
cd C:\Users\sapana.kumari\Downloads\LangGraph_MCP_Agent
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8001
```

Check it at `http://127.0.0.1:8001/health`.

### 4. React UI

```powershell
cd C:\Users\sapana.kumari\Downloads\LangGraph_MCP_Agent
npm --prefix web install
npm --prefix web run dev
```

Install Node.js LTS first if `npm` is not available. Open `http://localhost:5173` after Vite starts. The React UI calls only the FastAPI backend at `http://127.0.0.1:8001`; FastAPI owns the MCP and Optics service connections.

The previous Streamlit UI is retained in `frontend/ui.py` as a working reference during the transition, but it is not the primary UI.

Set `OPTICS_RAG_API_URL` in `.env` if Optics runs on another URL or port.

## Deploy with Docker Compose

The included Compose setup runs the React UI, FastAPI backend, and MCP tool service together. Only the web port is exposed publicly; Nginx routes API requests internally. Chat history is kept in a Docker volume across restarts. This works on a Linux VM such as Oracle Cloud Infrastructure and on other hosts with Docker Compose.

1. Install Docker Engine and the Docker Compose plugin on the host.
2. Copy or clone this project to the host and create its environment file:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set `GROQ_API_KEY` to a valid key. `TAVILY_API_KEY` is optional. For an Oracle VM, set `APP_PORT=80` to serve the app on standard HTTP; otherwise it defaults to port `8080`.
4. Build and start the services:

   ```bash
   docker compose up --build -d
   ```

5. Open `http://<your-vm-public-ip>/` (or `http://<your-vm-public-ip>:8080/` with the default port). Allow that TCP port in both the cloud network rules and the VM firewall.

Useful operations:

```bash
docker compose logs -f
docker compose ps
docker compose down
```

`docker compose down` keeps the `chat_data` volume. To back up chat history, back up that Docker volume. Document RAG is optional and still requires a separately reachable Optics RAG service; set `OPTICS_RAG_API_URL` in `.env` if you have one. The app can run without Optics for chat, weather, and web research. Do not commit `.env`; cloud deployments should provide real credentials through protected environment configuration.

To update after pulling new code, run `docker compose up --build -d` again.

## Run the terminal client

```powershell
python -m backend.cli
```

The backend must already be running. This client uses the same `/chat` API as the UI.

The React sidebar supports PDF, DOCX, XLSX, Markdown, and text uploads. Selecting a file sends it through the backend to Optics RAG. After it succeeds, you can ask the agent questions about that document immediately.

Example requests:

- `List files in ./data/documents`
- `What is the weather in Bangalore?`
- `Search the web for LangGraph MCP integration`
- `What does our employee handbook say about paid leave?`
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

Logs are separated by service: `logs/frontend.log`, `logs/backend.log`, and `logs/mcp-service.log`. The backend uses rotating JSON logs with a per-request `request_id`; the React UI sends only safe failure metadata to `/client-events`, so a browser error can be matched to backend activity. To protect private data, logs record question length rather than question text, and never record API keys, `.env` values, document content, or complete URL query strings.

Chat history is stored locally in SQLite at `data/chat_history.db`. Assistant artifact metadata, such as RAG citations and image references, is stored with the assistant reply so reopening the conversation keeps its sources visible.

The configured `GROQ_MODEL` is tried first. Set `GROQ_FALLBACK_MODELS` to a comma-separated list in `.env` to customize the fallback order; the default fallback is `openai/gpt-oss-20b`.

## Known limitations

- The command-line agent needs a reachable Groq API and a configured key.
- Public web search can use DuckDuckGo without a key; Tavily is recommended for more reliable structured search results.
- RAG requires the Optics FastAPI service and an already ingested collection.
- The scraper cleans common boilerplate and can try Crawl4AI for JavaScript-rendered pages when `CRAWL4AI_ENABLED=true`. Crawl4AI is optional; after installing dependencies, follow its browser-install instructions before enabling it. It does not bypass authentication, paywalls, or robots restrictions.

## Viva notes

LangGraph controls stateful, conditional LLM workflows; MCP lets clients discover and call external tool servers through typed schemas. Here `backend/mcp_client.py` connects to one `mcp_service/main.py` server, and LangGraph coordinates the agent/tool loop. A new capability is added by implementing a safe helper in `mcp_service/tools/`, exposing it with `@mcp.tool()` in `mcp_service/main.py`, and letting the backend discover its schema.
