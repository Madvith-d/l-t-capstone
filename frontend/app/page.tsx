"use client";
import { useEffect, useState } from "react";
import { BookMarked, CalendarRange, MessageSquareText, Search } from "lucide-react";
import { ChatWorkspace } from "@/components/ChatWorkspace";
import { DocumentsWorkspace } from "@/components/DocumentsWorkspace";
import { PlannerWorkspace } from "@/components/PlannerWorkspace";
import { api, Conversation, DemoStatus } from "@/lib/api";

type View = "chat" | "planner" | "documents";

export default function Home() {
  const [view, setView] = useState<View>("chat");
  const [conversationId, setConversationId] = useState<string>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [demo, setDemo] = useState<DemoStatus>({ enabled: false, label: "Live knowledge-base mode", questions: [] });

  useEffect(() => {
    Promise.all([api.conversations(), api.demoStatus()])
      .then(async ([items, status]) => {
        setDemo(status);
        if (status.enabled && items[0]) {
          const detail = await api.conversation(items[0].id);
          setConversations(items.map((item) => item.id === detail.id ? detail : item));
          setConversationId(detail.id);
        } else {
          setConversations(items);
        }
      })
      .catch(() => setConversations([]));
  }, []);

  useEffect(() => {
    function focusChat(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setView("chat");
        window.setTimeout(() => document.getElementById("question")?.focus(), 0);
      }
    }
    window.addEventListener("keydown", focusChat);
    return () => window.removeEventListener("keydown", focusChat);
  }, []);

  const selected = conversations.find((item) => item.id === conversationId);

  async function selectConversation(id: string) {
    setView("chat");
    try {
      const detail = await api.conversation(id);
      setConversations((items) => {
        const exists = items.some((item) => item.id === id);
        return exists ? items.map((item) => item.id === id ? detail : item) : [detail, ...items];
      });
      setConversationId(id);
    } catch { /* The next chat request will surface a typed connection error. */ }
  }

  return <main className="app-shell">
    <header className="topbar">
      <button className="wordmark" onClick={() => setView("chat")}><span>aa</span>academic-agent</button>
      <button className="search-pill" onClick={() => { setView("chat"); window.setTimeout(() => document.getElementById("question")?.focus(), 0); }}><Search size={16}/><span>Ask the academic corpus</span><kbd>⌘ K</kbd></button>
      <nav aria-label="Main navigation">
        <button className={view === "chat" ? "active" : ""} onClick={() => setView("chat")}><MessageSquareText/><span>Chat</span></button>
        <button className={view === "planner" ? "active" : ""} onClick={() => setView("planner")}><CalendarRange/><span>Planner</span></button>
        <button className={view === "documents" ? "active" : ""} onClick={() => setView("documents")}><BookMarked/><span>Sources</span></button>
      </nav>
    </header>
    <aside className="side-rail"><div><div className="rail-heading"><p>Conversations</p><span>{conversations.length}</span></div><button className="new-chat" onClick={() => { setConversationId(undefined); setView("chat"); }}>New conversation</button><div className="conversation-list">{conversations.map((conversation) => <button className={conversation.id === conversationId ? "active" : ""} key={conversation.id} onClick={() => void selectConversation(conversation.id)}>{conversation.title}</button>)}</div></div><div className="rail-note"><i/><span>Answers require evidence from the active source set.</span></div></aside>
    <div className="main-panel reveal">
      {view === "chat" && (
        <ChatWorkspace key={conversationId ?? "new"} conversationId={conversationId} demoQuestions={demo.questions} initialMessages={selected?.messages?.map((message) => ({ role: message.role as "user" | "assistant", content: message.content, sources: message.sources }))} onConversation={(id) => { void selectConversation(id); }}/>
      )}
      {view === "planner" && (
        <PlannerWorkspace/>
      )}
      {view === "documents" && (
        <DocumentsWorkspace demoMode={demo.enabled}/>
      )}
    </div>
    <footer className="foot-line"><p>Ask what the documents can prove.</p><div><span>academic-agent</span><span>Evidence-bound workspace</span></div></footer>
  </main>;
}
