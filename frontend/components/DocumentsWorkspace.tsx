"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { FileText, LoaderCircle, Upload } from "lucide-react";
import { api, Document } from "@/lib/api";

export function DocumentsWorkspace({ demoMode = false }: { demoMode?: boolean }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setDocuments(await api.documents());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Documents could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    api.documents()
      .then(setDocuments)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Documents could not be loaded."))
      .finally(() => setLoading(false));
  }, []);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setUploading(true);
    setError("");
    try {
      await api.ingestDocument(new FormData(form));
      form.reset();
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The document could not be ingested.");
    } finally {
      setUploading(false);
    }
  }

  return <section className="workspace documents">
    <header className="workspace__head">
      <div><p className="context-label">Source register</p><h1>Academic source material.</h1><p className="workspace__lede">Inspect the documents that academic answers are allowed to cite.</p></div>
      <span className="status">{documents.length} documents</span>
    </header>
    {!demoMode && <form className="planner-form document-upload" onSubmit={upload}>
      <label className="wide">PDF or text document<input name="file" type="file" accept=".pdf,.txt,application/pdf,text/plain" required /></label>
      <label>Title<input name="title" placeholder="Academic Regulations 2026" /></label>
      <label>Category<input name="category" placeholder="Regulations" /></label>
      <label>Department<input name="department" placeholder="Computer Science" /></label>
      <label>Academic year<input name="academic_year" placeholder="2025–26" /></label>
      <button className="primary" disabled={uploading}>{uploading ? <><LoaderCircle className="spinner" /> Ingesting…</> : <><Upload size={17} /> Add document</>}</button>
    </form>}
    {loading && <div className="thinking"><LoaderCircle className="spinner" /> Loading documents…</div>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {!loading && !error && documents.length === 0 && <div className="empty-state">
      <FileText /><h2>No documents ingested</h2>
      <p>Upload an approved PDF or TXT file. Its text will be cleaned, chunked, embedded, and stored for retrieval.</p>
    </div>}
    <div className="document-list">{documents.map((document) => <article key={document.id}>
      <FileText /><div><h2>{document.title}</h2><p>{[document.category, document.department, document.academic_year].filter(Boolean).join(" · ") || "Metadata not provided"}</p><small>{document.source}</small></div><span>{document.status}</span>
    </article>)}</div>
  </section>;
}
