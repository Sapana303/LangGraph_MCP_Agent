import { FormEvent, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Bot, CloudSun, FileSearch, FileText, Globe2, Network, Paperclip, Search, Send, Trash2, UserRound } from "lucide-react";
import { ApiError, type Message, fetchConversation, reportClientEvent, sendChat, uploadDocument } from "./api";

const tools = [
  [FileText, "FILES"],
  [CloudSun, "WEATHER"],
  [Search, "WEB SEARCH"],
  [Network, "OPTICS RAG"],
  [FileSearch, "SCRAPER"],
] as const;

function ArtifactView({ message }: { message: Message }) {
  const artifacts = message.artifacts;
  if (!artifacts) return null;
  return <div className="artifacts">
    {artifacts.image_base64 && <figure><img src={`data:image/png;base64,${artifacts.image_base64}`} alt="Related document" /><figcaption>Related image from Optics RAG</figcaption></figure>}
    {artifacts.web_image && <figure><img src={artifacts.web_image.image_url} alt={artifacts.web_image.caption} /><figcaption><a href={artifacts.web_image.source_url} target="_blank" rel="noreferrer">{artifacts.web_image.caption}</a></figcaption></figure>}
    {!!artifacts.sources?.length && <section className="sources"><b>Optics sources</b>{artifacts.sources.map((source, index) => <div className="source" key={`${source.source_file}-${source.page}-${index}`}><code>{source.source_file ?? "Indexed document"}</code><span>{source.section ?? "Unspecified section"} / Page {source.page ?? "-"}</span></div>)}</section>}
  </div>;
}

export default function App() {
  const [conversationId, setConversationId] = useState<string | null>(() => localStorage.getItem("mcp-atlas-conversation"));
  const [activeSource, setActiveSource] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  const conversation = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => fetchConversation(conversationId!),
    enabled: Boolean(conversationId),
  });

  const renderedMessages = useMemo(
    () => (messages.length ? messages : conversation.data?.messages ?? []),
    [conversation.data, messages],
  );

  const chat = useMutation({
    mutationFn: () => sendChat(question, conversationId, activeSource),
    onError: (error) => {
      void reportClientEvent("chat_failed", error instanceof ApiError ? error.code : error instanceof Error ? error.name.toUpperCase().replace(/[^A-Z0-9_]/g, "_") : "UNKNOWN_ERROR");
    },
    onSuccess: (data) => {
      void reportClientEvent("chat_completed");
      if (!conversationId) {
        setConversationId(data.conversation_id);
        localStorage.setItem("mcp-atlas-conversation", data.conversation_id);
      }
      setMessages((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: data.answer, artifacts: data.artifacts },
      ]);
      setQuestion("");
    },
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onError: (error) => {
      void reportClientEvent("document_upload_failed", error instanceof ApiError ? error.code : error instanceof Error ? error.name.toUpperCase().replace(/[^A-Z0-9_]/g, "_") : "UNKNOWN_ERROR");
    },
    onSuccess: (data) => {
      void reportClientEvent("document_upload_completed");
      setActiveSource(data.filename);
      setNotice(`Indexed ${data.chunks_added} chunks from ${data.filename}.`);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question.trim() && !chat.isPending) chat.mutate();
  }

  function resetConversation() {
    localStorage.removeItem("mcp-atlas-conversation");
    setConversationId(null);
    setMessages([]);
    setActiveSource(null);
    setNotice(null);
  }

  const error = chat.error ?? upload.error;

  return (
    <main className="shell">
      <aside className="rail">
        <div className="brand-wrap" aria-label="MCP Atlas">
          <div className="brand-mark">MCP</div>
          <div className="brand-copy">
            <span className="eyebrow">AGENTIC RESEARCH</span>
            <h2>ATLAS</h2>
          </div>
        </div>

        <div className="status-pill">
          <span className="live-dot" />
          Research system online
        </div>

        <div className="rail-section">
          <h2>AVAILABLE INSTRUMENTS</h2>
          <nav aria-label="Available tools" className="tool-list">
            {tools.map(([Icon, label], index) => (
              <div className="tool" key={label}>
                <span>0{index + 1}</span>
                <Icon size={17} />
                <b>{label}</b>
                <i title="Available" />
              </div>
            ))}
          </nav>
        </div>

        <div className="rail-section document-channel">
          <h2>DOCUMENT CHANNEL</h2>
          <label className="upload">
            <Paperclip size={17} />
            <span>
              {upload.isPending ? "Indexing document..." : "Choose source material"}
              <input
                type="file"
                accept=".pdf,.docx,.xlsx,.md,.txt"
                onChange={(event) => event.target.files?.[0] && upload.mutate(event.target.files[0])}
              />
            </span>
          </label>
        </div>

        {notice && <div className="notice">{notice}</div>}

        {activeSource && (
          <>
            <h2 className="scope-heading">RAG SCOPE</h2>
            <div className="active-source">{activeSource}</div>
          </>
        )}

        <button className="clear" onClick={resetConversation}>
          <Trash2 size={16} />
          New conversation
        </button>
      </aside>

      <section className="workspace">
        <header className="hero">
          <div className="hero-copy">
            <small>AGENTIC RESEARCH ATLAS</small>
            <h1>Trace answers across your documents and the web.</h1>
            <p>
              A connected workspace for grounded research, live signals, and clean source-backed insights.
            </p>
          </div>

          <div className="hero-metrics">
            <div className="status">
              <small>SYSTEM LINK</small>
              <strong>LIVE</strong>
            </div>
            <div className="array">
              <small>TOOL ARRAY</small>
              <strong>05 / READY</strong>
            </div>
          </div>
        </header>

        <div className="conversation-column">
          {error && (
            <div className="error">
              <b>{error instanceof ApiError ? error.code : "REQUEST_FAILED"}</b>
              <span>{error.message}</span>
            </div>
          )}

          <section className="thread" aria-live="polite">
            {conversation.isLoading ? (
              <p className="loading">Loading conversation...</p>
            ) : renderedMessages.length ? (
              renderedMessages.map((message, index) => (
                <article className={`message ${message.role}`} key={index}>
                  <div className="avatar">
                    {message.role === "user" ? <UserRound size={18} /> : <Bot size={18} />}
                  </div>
                  <div className="message-body">
                    <div className="content">
                      {message.role === "assistant" ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                      ) : (
                        message.content
                      )}
                    </div>
                    <ArtifactView message={message} />
                  </div>
                </article>
              ))
            ) : (
              <div className="empty">
                <span>RESEARCH THREAD</span>
                <b>Ready when you are.</b>
                <p>Ask about an uploaded document, a live topic, or a specific public page.</p>
              </div>
            )}
          </section>

          <form className="composer" onSubmit={submit}>
            <textarea
              value={question}
              placeholder="Ask a question"
              aria-label="Ask a question"
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit(event);
                }
              }}
            />
            <button aria-label="Send message" title="Send message" disabled={chat.isPending}>
              {chat.isPending ? "..." : <Send size={20} />}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
