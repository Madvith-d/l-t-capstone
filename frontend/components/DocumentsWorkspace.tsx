"use client";
import { useEffect, useState } from "react";
import { FileText, LoaderCircle } from "lucide-react";
import { api, Document } from "@/lib/api";

export function DocumentsWorkspace() {
  const [documents, setDocuments] = useState<Document[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  useEffect(() => { api.documents().then(setDocuments).catch((reason) => setError(reason instanceof Error ? reason.message : "Documents could not be loaded.")).finally(() => setLoading(false)); }, []);
  return <section className="workspace documents"><header className="workspace__head"><div><p className="context-label">Knowledge base</p><h1>Approved source material.</h1></div><span className="status">{documents.length} documents</span></header>{loading && <div className="thinking"><LoaderCircle className="spinner"/> Loading documents…</div>}{error && <p className="form-error">{error} Check the backend connection and retry.</p>}{!loading && !error && documents.length === 0 && <div className="empty-state"><FileText/><h2>No documents ingested</h2><p>Add a PDF or TXT file with the ingestion CLI. It will appear here after chunks and embeddings are stored.</p><code>python -m scripts.ingest data/raw/document.pdf</code></div>}<div className="document-list">{documents.map((document) => <article key={document.id}><FileText/><div><h2>{document.title}</h2><p>{[document.category, document.department, document.academic_year].filter(Boolean).join(" · ") || "Metadata not provided"}</p><small>{document.source}</small></div><span>{document.status}</span></article>)}</div></section>;
}
