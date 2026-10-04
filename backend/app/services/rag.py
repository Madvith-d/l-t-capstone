import logging
import time
from dataclasses import dataclass

from app.schemas.api import Source
from app.services.llm import LLMService, get_llm_service
from app.services.prompts import UNKNOWN_RESPONSE
from app.services.retrieval import RetrievedChunk, Retriever

logger = logging.getLogger("rag")


@dataclass
class PreparedContext:
    context: str
    sources: list[Source]
    confidence: float
    chunks: list[RetrievedChunk]


class RAGService:
    def __init__(self, retriever: Retriever, llm: LLMService | None = None):
        self.retriever = retriever
        self.llm = llm or get_llm_service()

    @staticmethod
    def contextualize(question: str, history: list[dict] | None = None) -> str:
        """Resolve short follow-ups with bounded recent user context."""
        if history and len(question.split()) < 12:
            previous = [
                str(message["content"])
                for message in history[-4:]
                if message.get("role") == "user" and message.get("content")
            ]
            return " ".join(previous + [question])
        return question

    def prepare(
        self,
        question: str,
        history: list[dict] | None = None,
        filters: dict[str, str] | None = None,
    ) -> PreparedContext:
        chunks = self.retriever.retrieve(
            self.contextualize(question, history),
            filters=filters,
        )
        context_parts: list[str] = []
        sources: list[Source] = []
        for index, item in enumerate(chunks, 1):
            context_parts.append(
                f"Source [{index}] — {item.document.title}, "
                f"page {item.chunk.page_number or 'unknown'}:\n{item.chunk.content}"
            )
            sources.append(
                Source(
                    document_id=item.document.id,
                    title=item.document.title,
                    page=item.chunk.page_number,
                    section=item.chunk.section,
                    category=item.document.category,
                    department=item.document.department,
                    academic_year=item.document.academic_year,
                    source=item.document.source,
                    score=round(item.score, 4),
                )
            )
        return PreparedContext(
            context="\n\n".join(context_parts),
            sources=sources,
            confidence=max((item.score for item in chunks), default=0.0),
            chunks=chunks,
        )

    def generate(
        self,
        question: str,
        prepared: PreparedContext,
        history: list[dict] | None = None,
    ) -> str:
        if not prepared.chunks:
            return UNKNOWN_RESPONSE
        started = time.perf_counter()
        answer = self.llm.answer(question, prepared.context, history)
        logger.info(
            "retrieved_chunk_ids=%s retrieval_scores=%s llm_latency_ms=%.2f",
            [item.chunk.id for item in prepared.chunks],
            [round(item.score, 4) for item in prepared.chunks],
            (time.perf_counter() - started) * 1000,
        )
        return answer

    def answer(
        self,
        question: str,
        history: list[dict] | None = None,
        filters: dict[str, str] | None = None,
    ) -> tuple[str, list[Source], float]:
        """Backward-compatible complete RAG operation for scripts and direct callers."""
        prepared = self.prepare(question, history, filters)
        answer = self.generate(question, prepared, history)
        return answer, prepared.sources, prepared.confidence
