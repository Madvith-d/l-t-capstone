import logging
import time

from app.schemas.api import Source
from app.services.llm import LLMService, get_llm_service
from app.services.retrieval import Retriever

logger = logging.getLogger("rag")


class RAGService:
    def __init__(self, retriever: Retriever, llm: LLMService | None = None):
        self.retriever = retriever
        self.llm = llm or get_llm_service()

    def answer(
        self,
        question: str,
        history: list[dict] | None = None,
        filters: dict[str, str] | None = None,
    ) -> tuple[str, list[Source], float]:
        # Recent user context helps resolve short follow-ups without unbounded history.
        enriched_query = question
        if history and len(question.split()) < 12:
            previous = [m["content"] for m in history[-4:] if m.get("role") == "user"]
            enriched_query = " ".join(previous + [question])
        chunks = self.retriever.retrieve(enriched_query, filters=filters)
        if not chunks:
            return (
                "I couldn't find information about this in the available college documents.",
                [],
                0.0,
            )
        context_parts, sources = [], []
        for index, item in enumerate(chunks, 1):
            context_parts.append(
                f"Source [{index}] — {item.document.title}, page {item.chunk.page_number or 'unknown'}:\n{item.chunk.content}"
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
        started = time.perf_counter()
        answer = self.llm.answer(question, "\n\n".join(context_parts), history)
        logger.info(
            "retrieved_chunk_ids=%s retrieval_scores=%s llm_latency_ms=%.2f",
            [item.chunk.id for item in chunks],
            [round(item.score, 4) for item in chunks],
            (time.perf_counter() - started) * 1000,
        )
        return answer, sources, max(item.score for item in chunks)
