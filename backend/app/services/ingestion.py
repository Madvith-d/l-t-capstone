import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Document, DocumentChunk
from app.services.embeddings import EmbeddingService, get_embedding_service

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


@dataclass
class PageText:
    number: int | None
    text: str


@dataclass
class Chunk:
    content: str
    page_number: int | None
    section: str | None


def clean_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\u00ad", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_document(path: Path) -> list[PageText]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported document type: {suffix}")
    if suffix == ".txt":
        return [PageText(None, clean_text(path.read_text(encoding="utf-8", errors="replace")))]
    try:
        reader = PdfReader(str(path))
        pages = [
            PageText(index, clean_text(page.extract_text() or ""))
            for index, page in enumerate(reader.pages, 1)
        ]
    except Exception as exc:
        raise ValueError("The PDF could not be parsed") from exc
    # Remove repeated short first/last lines when they occur on most pages.
    candidates: dict[str, int] = {}
    for page in pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for line in lines[:1] + lines[-1:]:
            if len(line) < 120:
                candidates[line] = candidates.get(line, 0) + 1
    repeated = {
        line for line, count in candidates.items() if len(pages) > 2 and count >= len(pages) * 0.6
    }
    return [
        PageText(
            p.number,
            "\n".join(line for line in p.text.splitlines() if line.strip() not in repeated),
        )
        for p in pages
        if p.text
    ]


def estimate_tokens(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)) * 4 // 3)


def chunk_pages(
    pages: list[PageText], size: int = 850, overlap: int = 125, default_section: str | None = None
) -> list[Chunk]:
    chunks: list[Chunk] = []
    words_per_chunk = max(50, size * 3 // 4)
    overlap_words = overlap * 3 // 4
    step = max(1, words_per_chunk - overlap_words)
    for page in pages:
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", page.text) if item.strip()]
        text = "\n\n".join(paragraphs)
        words = text.split()
        section = default_section
        for candidate in paragraphs:
            if len(candidate) < 100 and (candidate.isupper() or candidate.endswith(":")):
                section = candidate.rstrip(":")
                break
        for start in range(0, len(words), step):
            content = " ".join(words[start : start + words_per_chunk]).strip()
            if content:
                chunks.append(Chunk(content, page.number, section))
            if start + words_per_chunk >= len(words):
                break
    return chunks


class IngestionService:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        settings: Settings | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.embeddings = embeddings or get_embedding_service(self.settings)

    def ingest(self, path: Path, metadata: dict | None = None) -> tuple[Document, bool]:
        metadata = metadata or {}
        raw = path.read_bytes()
        content_hash = hashlib.sha256(raw).hexdigest()
        pages = load_document(path)
        chunks = chunk_pages(
            pages,
            self.settings.chunk_size_tokens,
            self.settings.chunk_overlap_tokens,
            metadata.get("section"),
        )
        if not chunks or not any(chunk.content.strip() for chunk in chunks):
            raise ValueError("The document contains no searchable text. Scanned PDFs require OCR.")
        existing = self.db.scalar(select(Document).where(Document.content_hash == content_hash))
        title = metadata.get("title") or path.stem.replace("-", " ").title()
        source = metadata.get("source") or str(path)
        if existing:
            stored_model = (
                existing.chunks[0].metadata_.get("embedding_model") if existing.chunks else None
            )
            if stored_model == self.embeddings.model_name:
                changed = any(
                    getattr(existing, field) != value
                    for field, value in {
                        "title": title,
                        "category": metadata.get("category"),
                        "department": metadata.get("department"),
                        "academic_year": metadata.get("academic_year"),
                        "source": source,
                    }.items()
                )
                if changed:
                    existing.title = title
                    existing.category = metadata.get("category")
                    existing.department = metadata.get("department")
                    existing.academic_year = metadata.get("academic_year")
                    existing.source = source
                    for chunk in existing.chunks:
                        chunk.metadata_ = {
                            **chunk.metadata_,
                            **metadata,
                            "title": title,
                            "source": source,
                        }
                    self.db.commit()
                    self.db.refresh(existing)
                return existing, False
            self.db.delete(existing)
            self.db.flush()
        vectors = self.embeddings.embed_documents([chunk.content for chunk in chunks])
        document = Document(
            id=content_hash[:32],
            title=title,
            category=metadata.get("category"),
            department=metadata.get("department"),
            academic_year=metadata.get("academic_year"),
            source=source,
            content_hash=content_hash,
            status="processing",
        )
        try:
            self.db.add(document)
            self.db.flush()
            for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
                self.db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        section=chunk.section,
                        metadata_={
                            "document_id": document.id,
                            "title": document.title,
                            "source": source,
                            "embedding_model": self.embeddings.model_name,
                            **metadata,
                        },
                        embedding=vector,
                    )
                )
            document.status = "ready"
            self.db.commit()
            self.db.refresh(document)
            return document, True
        except Exception:
            self.db.rollback()
            raise
