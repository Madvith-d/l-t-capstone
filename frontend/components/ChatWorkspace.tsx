"use client";
import { FormEvent, useState } from "react";
import { ArrowUp, BookOpen, LoaderCircle } from "lucide-react";
import { api, Source } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string; sources?: Source[] };

export function ChatWorkspace({ conversationId, initialMessages = [], onConversation }: { conversationId?: string; initialMessages?: Message[]; onConversation: (id: string) => void }) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function send(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (!value || loading) return;
    setQuestion(""); setError(""); setMessages((items) => [...items, { role: "user", content: value }]); setLoading(true);
    try {
      const result = await api.chat(value, conversationId);
      onConversation(result.conversation_id);
      setMessages((items) => [...items, { role: "assistant", content: result.answer, sources: result.sources }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The assistant could not answer. Try again.");
    } finally { setLoading(false); }
  }

  return <section className="workspace" aria-labelledby="chat-heading">
    <header className="workspace__head"><div><p className="context-label">Grounded assistant</p><h1 id="chat-heading">Ask the documents.</h1></div><span className="status"><i /> Evidence required</span></header>
    <div className="messages" aria-live="polite">
      {messages.length === 0 && <div className="empty-state"><BookOpen aria-hidden="true"/><h2>Start with a college question</h2><p>Ask about regulations, examinations, attendance, or a syllabus. Answers include document references when evidence is available.</p><div className="prompt-row"><button onClick={() => setQuestion("What is the attendance requirement?")}>Attendance requirement</button><button onClick={() => setQuestion("What subjects are in semester 4?")}>Semester 4 subjects</button></div></div>}
      {messages.map((message, index) => <article className={`message message--${message.role}`} key={`${message.role}-${index}`}><span className="message__role">{message.role === "user" ? "You" : "Northstar"}</span><p>{message.content}</p>{message.sources?.length ? <div className="sources"><h3>Sources</h3>{message.sources.map((source) => <div className="source" key={`${source.document_id}-${source.page}`}><BookOpen size={16}/><span><strong>{source.title}</strong><small>{source.page ? `Page ${source.page}` : "Page unavailable"}{source.section ? ` · ${source.section}` : ""}</small></span></div>)}</div> : null}</article>)}
      {loading && <div className="thinking"><LoaderCircle className="spinner" aria-hidden="true"/> Searching approved documents…</div>}
    </div>
    {error && <p className="form-error" role="alert">{error} Check that the backend is running, then try again.</p>}
    <form className="composer" onSubmit={send}><label htmlFor="question">Your question</label><div className="composer__row"><textarea id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask a specific academic question…" rows={2}/><button className="send" disabled={!question.trim() || loading} aria-label="Send question">{loading ? <LoaderCircle className="spinner"/> : <ArrowUp/>}</button></div><small>College-specific answers are withheld when the documents do not contain enough evidence.</small></form>
  </section>;
}
