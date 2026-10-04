"use client";
import { FormEvent, useState } from "react";
import { ArrowUp, BookOpen, LoaderCircle } from "lucide-react";
import { api, Source } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };

export function ChatWorkspace({ conversationId, initialMessages = [], demoQuestions = [], onConversation }: { conversationId?: string; initialMessages?: Message[]; demoQuestions?: string[]; onConversation: (id: string) => void }) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [retryQuestion, setRetryQuestion] = useState("");

  async function send(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (!value || loading) return;
    setQuestion(""); setError(""); setRetryQuestion(value); setMessages((items) => [...items, { role: "user", content: value }]); setLoading(true);
    try {
      const result = await api.chat(value, conversationId);
      onConversation(result.conversation_id);
      setMessages((items) => [...items, { role: "assistant", content: result.answer, sources: result.sources }]);
      setRetryQuestion("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The assistant could not answer. Try again.");
    } finally { setLoading(false); }
  }

  return <section className="workspace" aria-labelledby="chat-heading">
    <header className="workspace__head"><div><p className="context-label">Academic workspace</p><h1 id="chat-heading">Ask with evidence.</h1><p className="workspace__lede">Questions become grounded answers, study plans, or deliberate tool actions.</p></div><span className="status"><i /> Sources enforced</span></header>
    <div className="messages" aria-live="polite">
      {messages.length === 0 && <div className="empty-state"><BookOpen aria-hidden="true"/><h2>Start with a precise question</h2><p>Ask about regulations, examinations, attendance, or a syllabus. Every academic answer names its evidence.</p><div className="prompt-row">{(demoQuestions.length ? demoQuestions.slice(0, 4) : ["What is the attendance requirement?", "What subjects are in semester 4?"]).map((prompt) => <button key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}</div></div>}
      {messages.map((message, index) => <article className={`message message--${message.role}`} key={`${message.role}-${index}`}><span className="message__role">{message.role === "user" ? "You" : "academic-agent"}</span><p>{message.content}</p>{message.sources?.length ? <div className="sources"><h3>Sources</h3>{message.sources.map((source) => <div className="source" key={`${source.document_id}-${source.page}`}><BookOpen size={16}/><span><strong>{source.title}</strong><small>{source.page ? `Page ${source.page}` : "Page unavailable"}{source.section ? ` · ${source.section}` : ""}</small></span></div>)}</div> : null}</article>)}
      {loading && <div className="thinking"><LoaderCircle className="spinner" aria-hidden="true"/> Searching approved documents…</div>}
    </div>
    {error && <div className="form-error" role="alert"><p>{error}</p>{retryQuestion && <button type="button" onClick={() => { setQuestion(retryQuestion); setError(""); }}>Retry</button>}</div>}
    <form className="composer" onSubmit={send}><label htmlFor="question">Your question</label><div className="composer__row"><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a specific academic question…" rows={2}/><button className="send" disabled={!question.trim() || loading} aria-label="Send question">{loading ? <LoaderCircle className="spinner"/> : <ArrowUp/>}</button></div><small>College-specific answers are withheld when the documents do not contain enough evidence.</small></form>
  </section>;
}
