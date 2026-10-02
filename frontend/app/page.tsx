"use client";
import { useEffect, useState } from "react";
import { BookMarked, CalendarRange, MessageSquareText, Search } from "lucide-react";
import { ChatWorkspace } from "@/components/ChatWorkspace";
import { DocumentsWorkspace } from "@/components/DocumentsWorkspace";
import { PlannerWorkspace } from "@/components/PlannerWorkspace";
import { api, Conversation } from "@/lib/api";

type View = "chat" | "planner" | "documents";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<Conversation[]>([]);

  function refreshConversations() {
    api.conversations().then(setConversations).catch(() => setConversations([]));
  }

  useEffect(refreshConversations, []);
  const selected = conversations.find((item) => item.id === conversationId);

  return <main className="app-shell">
    <header className="topbar"><button className="wordmark" onClick={() => setView("chat")}><span>N</span>Northstar</button><button className="search-pill" onClick={() => setView("chat")}><Search size={16}/><span>Ask academic documents…</span><kbd>⌘ K</kbd></button><nav aria-label="Main navigation"><button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}><MessageSquareText/>Chat</button><button className={view === "planner" ? "active" : ""} onClick={() => setView("planner")}><CalendarRange/>Planner</button><button className={view === "documents" ? "active" : ""} onClick={() => setView("documents")}><BookMarked/>Sources</button></nav></header>
    <aside className="side-rail"><div><p>Conversations</p><button className="new-chat" onClick={() => { setConversationId(undefined); setView("chat"); }}>New conversation</button><div className="conversation-list">{conversations.map((conversation) => <button className={conversation.id === conversationId ? "active" : ""} key={conversation.id} onClick={() => { setConversationId(conversation.id); setView("chat"); }}>{conversation.title}</button>)}</div></div><div className="rail-note"><i/><span>Answers cite ingested sources. Missing evidence is reported, not guessed.</span></div></aside>
    <div className="main-panel reveal">{view === "chat" && <ChatWorkspace key={conversationId ?? "new"} conversationId={conversationId} initialMessages={selected?.messages.map((message) => ({ role: message.role as "user" | "assistant", content: message.content, sources: message.sources }))} onConversation={(id) => { setConversationId(id); refreshConversations(); }}/>} {view === "planner" && <PlannerWorkspace/>} {view === "documents" && <DocumentsWorkspace/>}</div>
    <footer className="foot-line"><span>Northstar · Academic evidence, conversations, and plans</span><span>Local-first development mode</span></footer>
  </main>;
}
