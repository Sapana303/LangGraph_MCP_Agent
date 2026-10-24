"""Streamlit interface for the LangGraph MCP assistant."""

from __future__ import annotations

import base64
import html

import requests
import streamlit as st

try:  # Supports both `streamlit run frontend/ui.py` and package imports.
    from frontend.api_client import BackendUnavailableError, ask_backend, ingest_document
    from frontend.config import BACKEND_API_URL
    from frontend.logging_utils import get_logger
except ModuleNotFoundError:
    from api_client import BackendUnavailableError, ask_backend, ingest_document
    from config import BACKEND_API_URL
    from logging_utils import get_logger


logger = get_logger(__name__)
USER_AVATAR = ":material/person:"
ASSISTANT_AVATAR = ":material/hub:"


st.set_page_config(page_title="MCP Field Desk", page_icon="M", layout="wide", initial_sidebar_state="expanded")


def backend_status() -> tuple[bool, str]:
    try:
        response = requests.get(f"{BACKEND_API_URL}/health", timeout=3)
        if not response.ok:
            logger.warning("Backend health check returned status=%d", response.status_code)
        return response.ok, "LINKED" if response.ok else "OFFLINE"
    except requests.RequestException as error:
        logger.warning("Backend health check failed error_type=%s", type(error).__name__)
        return False, "OFFLINE"


def ingest_uploaded_file(uploaded_file) -> dict:
    logger.info("UI ingestion started filename=%s size_bytes=%d", uploaded_file.name, uploaded_file.size)
    result = ingest_document(uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
    logger.info(
        "UI ingestion completed filename=%s chunks_added=%s",
        result.get("filename", uploaded_file.name), result.get("chunks_added", "unknown"),
    )
    return result


def render_rag_artifacts(artifacts: dict | None) -> None:
    """Render source details and a retrieved Optics image outside the model context."""
    if not artifacts:
        return
    image_base64 = artifacts.get("image_base64")
    if image_base64:
        try:
            st.image(base64.b64decode(image_base64), caption="Related image from Optics RAG")
        except (ValueError, TypeError):
            st.caption("Optics returned an image that could not be displayed.")
    sources = artifacts.get("sources", [])
    if sources:
        st.markdown("**Optics sources**")
        seen_sources = set()
        for source in sources:
            source_file = html.escape(str(source.get("source_file") or "Indexed document"))
            section = html.escape(str(source.get("section") or "Unspecified section"))
            page = source.get("page")
            source_key = (source_file, section, page)
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            page_text = f"Page {page}" if page else "Page unavailable"
            st.markdown(
                f'<div class="source-record"><div class="source-file">{source_file}</div>'
                f'<div class="source-meta"><span>{section}</span><span>{page_text}</span></div></div>',
                unsafe_allow_html=True,
            )


st.markdown(
    """
    <style>
      :root { --ink:#11201b; --paper:#f6f4ee; --line:#c8cec5; --signal:#d9ff4b; --coral:#ff694d; --blue:#1e7182; --muted:#617069; --panel:#e8eee7; }
      .stApp { background:var(--paper); color:var(--ink); }
      [data-testid="stMain"] { color:var(--ink); }
      [data-testid="stMain"] .stMarkdown, [data-testid="stMain"] .stMarkdown p, [data-testid="stMain"] .stMarkdown li { color:var(--ink); }
      [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] { background:var(--paper) !important; }
      [data-testid="stSidebar"] { background:#102019; min-width:308px; border-right:1px solid #314439; }
      [data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding:1.35rem 1.05rem 1rem; }
      [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption { color:#edf2ec !important; }
      [data-testid="stSidebar"] hr { border-color:#365045; margin:1.35rem 0; }
      [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { background:#172920; border:1px dashed #71867a; border-radius:4px; }
      [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * { color:#edf2ec !important; }
      [data-testid="stSidebar"] button { border-radius:4px; border:1px solid #d9ff4b; min-height:2.8rem; }
      [data-testid="stSidebar"] button[kind="primary"] { background:var(--signal); color:var(--ink); }
      [data-testid="stSidebar"] button[kind="secondary"] { background:#172920; color:#edf2ec; border-color:#60766a; }
      [data-testid="stSidebar"] [role="radiogroup"] label, [data-testid="stSidebar"] [role="radiogroup"] p { color:#edf2ec !important; }
      [data-testid="stHeader"] { background:transparent; }
      .block-container { max-width:1320px; padding-top:1.7rem; padding-bottom:1rem; }
      .eyebrow { font-size:.72rem; font-weight:800; letter-spacing:0; color:var(--blue); }
      .desk-title { font-size:2.7rem; line-height:.96; font-weight:800; letter-spacing:0; margin:.4rem 0 0; }
      .desk-subtitle { max-width:44rem; font-size:1.03rem; color:var(--muted); margin-top:.8rem; }
      .signal-box { min-height:4.8rem; border-left:4px solid var(--coral); padding:.35rem 0 .35rem .85rem; margin-top:.45rem; }
      .signal-label { color:var(--muted); font-size:.68rem; font-weight:800; }
      .signal-value { color:var(--ink); font-weight:850; font-size:1rem; }
      .metric-box { border-left:1px solid var(--line); padding:.35rem 0 .35rem .85rem; margin-top:.45rem; }
      .metric-label { color:var(--muted); font-size:.68rem; font-weight:800; }
      .metric-value { color:var(--blue); font-family:monospace; font-size:1rem; font-weight:800; margin-top:.15rem; }
      .desk-rule { border:0; border-top:1px solid var(--ink); margin:1.9rem 0 .75rem; }
      .rail-brand { color:var(--signal); font-size:2.1rem; font-weight:850; line-height:.84; }
      .rail-meta { color:#a8b6ac; font-size:.7rem; font-weight:800; margin-top:.6rem; }
      .rail-section { color:#9eb0a5; font-size:.68rem; font-weight:800; margin:1.25rem 0 .55rem; }
      .tool-row { display:flex; align-items:center; justify-content:space-between; border-top:1px solid #365045; padding:.72rem 0; font-size:.86rem; }
      .tool-index { color:var(--signal); font-family:monospace; font-weight:800; min-width:2.2rem; }
      .tool-name { flex:1; color:#edf2ec; font-weight:650; }
      .tool-state { width:.42rem; height:.42rem; border-radius:50%; background:#5f776a; }
      .link-state, .link-offline { display:inline-flex; align-items:center; gap:.42rem; font-size:.74rem; font-weight:850; }
      .link-state { color:var(--signal); }
      .link-state::before { content:""; width:.48rem; height:.48rem; border-radius:50%; background:var(--signal); }
      .link-offline { color:#ff937b; }
      .link-offline::before { content:""; width:.48rem; height:.48rem; border-radius:50%; background:#ff937b; }
      [data-testid="stChatMessage"] { background:transparent; border-top:1px solid var(--line); border-radius:0; padding:1.25rem .3rem; }
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { border-top:2px solid var(--ink); }
      [data-testid="stChatMessageContent"] { color:var(--ink); }
      [data-testid="stChatMessageContent"] p, [data-testid="stChatMessageContent"] li,
      [data-testid="stChatMessageContent"] h1, [data-testid="stChatMessageContent"] h2,
      [data-testid="stChatMessageContent"] h3, [data-testid="stChatMessageContent"] h4,
      [data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td { color:var(--ink) !important; }
      [data-testid="stChatMessageContent"] a { color:var(--blue) !important; text-decoration-thickness:1px; }
      [data-testid="stChatMessageContent"] :not(pre) > code {
        background:#e1e9e0 !important; color:#18372a !important; border:1px solid #b7c9b8;
        border-radius:3px; padding:.1rem .28rem; font-family:monospace;
      }
      [data-testid="stChatMessageContent"] pre {
        background:#16251e !important; border:1px solid #405e4d; border-radius:4px; padding:.85rem;
      }
      [data-testid="stChatMessageContent"] pre, [data-testid="stChatMessageContent"] pre * {
        color:#edf4e9 !important; background:transparent !important;
      }
      [data-testid="stChatMessageContent"] table { border-collapse:collapse; width:100%; }
      [data-testid="stChatMessageContent"] th { background:#e3e9e0; }
      [data-testid="stChatMessageContent"] th, [data-testid="stChatMessageContent"] td { border:1px solid #bdc8bd; padding:.45rem .55rem; }
      [data-testid="stChatMessageContent"] blockquote { border-left:3px solid var(--coral); color:#405047; margin-left:0; padding-left:.8rem; }
      [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"] { background:var(--coral); color:#24140f; border-radius:50%; }
      [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] { background:var(--blue); color:#fff; border-radius:50%; }
      [data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] div[data-baseweb="textarea"] { border:1px solid var(--ink); border-radius:4px; background:#fffdf8 !important; }
      [data-testid="stChatInput"] textarea, [data-testid="stChatInput"] textarea::placeholder, [data-testid="stChatInput"] input, [data-testid="stChatInput"] [contenteditable="true"] { color:var(--ink) !important; background:#fff !important; font-size:1rem; }
      [data-testid="stChatInputSubmitButton"] { background:var(--coral) !important; color:#fff !important; }
      [data-testid="stChatInputSubmitButton"] * { color:#fff !important; }
      .empty-state { border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:2.35rem 0; margin-top:1rem; color:var(--muted); }
      .empty-state b { color:var(--ink); }
      .source-record { border-top:1px solid var(--line); padding:.8rem 0; color:var(--ink); }
      .source-file { color:#18251d; font-family:monospace; font-size:.82rem; font-weight:700; overflow-wrap:anywhere; }
      .source-meta { display:flex; flex-wrap:wrap; gap:.5rem; color:var(--muted); font-size:.88rem; margin-top:.18rem; }
      .source-meta span + span::before { content:"/"; margin-right:.5rem; color:#9aa59e; }
      .active-source { border-left:3px solid var(--signal); background:#172920; color:#edf2ec; font-family:monospace; font-size:.78rem; overflow-wrap:anywhere; padding:.55rem .6rem; margin:.3rem 0 .65rem; border-radius:0 3px 3px 0; }
      @media (max-width:700px) { .desk-title { font-size:2.1rem; } .block-container { padding-left:1rem; padding-right:1rem; } .metric-box { display:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "active_source_file" not in st.session_state:
    st.session_state.active_source_file = None
if "ingestion_notice" not in st.session_state:
    st.session_state.ingestion_notice = None

online, status = backend_status()
link_class = "link-state" if online else "link-offline"

with st.sidebar:
    st.markdown('<div class="rail-brand">MCP<br>ATLAS</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-meta">LANGGRAPH / RESEARCH SYSTEM</div>', unsafe_allow_html=True)
    st.markdown('<div class="rail-section">AVAILABLE INSTRUMENTS</div>', unsafe_allow_html=True)
    for index, name in enumerate(("FILES", "WEATHER", "WEB SEARCH", "OPTICS RAG", "SCRAPER"), start=1):
        st.markdown(
            f'<div class="tool-row"><span class="tool-index">0{index}</span>'
            f'<span class="tool-name">{name}</span><span class="tool-state"></span></div>',
            unsafe_allow_html=True,
        )
    st.divider()
    st.markdown('<div class="rail-section">BACKEND LINK</div>', unsafe_allow_html=True)
    st.markdown(f'<span class="{link_class}">LANGGRAPH API / {status}</span>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("SOURCE MATERIAL", type=["pdf", "docx", "xlsx", "md", "txt"])
    if st.button("Index document", disabled=uploaded_file is None or not online, type="primary", use_container_width=True):
        try:
            with st.spinner("Extracting, embedding, and indexing document..."):
                result = ingest_uploaded_file(uploaded_file)
            filename = result.get("filename", uploaded_file.name)
            st.session_state.active_source_file = filename
            st.session_state.ingestion_notice = f"Indexed {result.get('chunks_added', 0)} chunks from {filename}."
        except BackendUnavailableError as error:
            logger.warning("UI ingestion failed filename=%s error=%s", uploaded_file.name, error)
            st.error("Could not index the document. Check the backend and Optics RAG services.")
    if uploaded_file and st.session_state.active_source_file != uploaded_file.name:
        if st.button("Use selected document for RAG", use_container_width=True):
            st.session_state.active_source_file = uploaded_file.name
            st.rerun()
    if st.session_state.ingestion_notice:
        st.success(st.session_state.ingestion_notice)
    if st.session_state.active_source_file:
        st.markdown('<div class="rail-section">RAG SCOPE</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="active-source">{html.escape(st.session_state.active_source_file)}</div>', unsafe_allow_html=True)
        scope = st.radio(
            "Search scope",
            ("Active document", "All indexed documents"),
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        scope = "All indexed documents"
    st.divider()
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

header, signal, metric = st.columns([4, 1, 1])
with header:
    st.markdown('<div class="eyebrow">AGENTIC RESEARCH ATLAS</div>', unsafe_allow_html=True)
    st.markdown('<div class="desk-title">Trace answers across<br>your documents and the web.</div>', unsafe_allow_html=True)
    st.markdown('<div class="desk-subtitle">A connected workspace for grounded research, live signals, and clear sources.</div>', unsafe_allow_html=True)
with signal:
    st.markdown(f'<div class="signal-box"><div class="signal-label">SYSTEM LINK</div><div class="signal-value">{status}</div></div>', unsafe_allow_html=True)
with metric:
    st.markdown('<div class="metric-box"><div class="metric-label">TOOL ARRAY</div><div class="metric-value">05 / READY</div></div>', unsafe_allow_html=True)

st.markdown('<hr class="desk-rule">', unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown('<div class="empty-state"><b>Research thread ready.</b><br>Your next question becomes the first point on the map.</div>', unsafe_allow_html=True)

for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else ASSISTANT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            render_rag_artifacts(message.get("artifacts"))

prompt = st.chat_input("Ask a question")
if prompt:
    previous_messages = list(st.session_state.messages)
    logger.info(
        "UI question started prompt_chars=%d history_messages=%d scope=%s",
        len(prompt), len(previous_messages), scope,
    )
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.spinner("Routing request..."):
            try:
                source_filter = st.session_state.active_source_file if scope == "Active document" else None
                answer, artifacts = ask_backend(prompt, previous_messages, source_filter)
                logger.info("UI question completed artifacts=%s", bool(artifacts))
            except BackendUnavailableError as error:
                logger.warning("UI could not reach backend error=%s", error)
                answer = "The LangGraph backend is unavailable. Start it with `uvicorn backend.main:app --reload --port 8001`."
                artifacts = None
            except Exception as error:
                logger.exception("UI question failed error_type=%s", type(error).__name__)
                answer = "I could not complete that request. Check the configured model, network access, and tool services."
                artifacts = None
        st.markdown(answer)
        render_rag_artifacts(artifacts)
    st.session_state.messages.append({"role": "assistant", "content": answer, "artifacts": artifacts})
