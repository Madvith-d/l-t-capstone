import logging
import re
import time
from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.schemas.api import Source
from app.services.llm import LLMService, get_llm_service
from app.services.prompts import UNKNOWN_RESPONSE
from app.services.retrieval import RetrievedChunk, Retriever

logger = logging.getLogger("rag")
STOP_WORDS = {
    "about", "after", "and", "are", "does", "find", "from", "have", "identify",
    "into", "that", "the", "their", "this", "what", "when", "which", "with", "will",
}


@dataclass
class PreparedContext:
    context: str
    sources: list[Source]
    confidence: float
    chunks: list[RetrievedChunk]
    evidence_sufficient: bool
    query: str


def query_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def rewrite_query(question: str, history: list[dict] | None = None) -> str:
    """Convert a short referential follow-up into one concise retrieval query."""
    if not history or len(question.split()) >= 12:
        return question.strip()
    if not re.search(r"\b(it|that|those|them|this|they)\b", question, re.IGNORECASE):
        return question.strip()
    previous_question = next(
        (
            str(message.get("content", "")).strip()
            for message in reversed(history[-6:])
            if message.get("role") == "user" and message.get("content")
        ),
        "",
    )
    if not previous_question:
        return question.strip()
    subject = re.sub(
        r"^(?:what|which|when|where)\s+(?:is|are|was|were)\s+(?:the\s+)?",
        "",
        previous_question.rstrip("?. "),
        flags=re.IGNORECASE,
    )
    if subject and re.search(r"\bit\b", question, re.IGNORECASE):
        return re.sub(r"\bit\b", f"the {subject}", question, flags=re.IGNORECASE)
    return f"{previous_question.rstrip('?.')} — {question.strip()}"


def validate_citations(answer: str, source_count: int) -> tuple[str, list[str]]:
    """Remove invalid markers and ensure grounded answers have one valid marker."""
    notes: list[str] = []
    if UNKNOWN_RESPONSE.lower() in answer.lower():
        return UNKNOWN_RESPONSE, ["normalized_model_no_evidence_response"]

    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 1 <= index <= source_count:
            return match.group(0)
        notes.append(f"removed_invalid_citation_{index}")
        return ""

    cleaned = re.sub(r"\[(\d+)\]", replace, answer)
    cleaned = re.sub(r"\s+([.,])", r"\1", cleaned).strip()
    if source_count and not re.search(r"\[(\d+)\]", cleaned):
        cleaned = f"{cleaned} [1]"
        notes.append("added_authoritative_source_marker_1")
    return cleaned, notes


def decompose_query(question: str, limit: int = 3) -> list[str]:
    parts = re.split(r"\s+(?:and then|and|then)\s+", question, flags=re.IGNORECASE)
    meaningful = [
        re.sub(r"^(?:find|identify|list|show|compare)\s+(?:the\s+)?", "", part.strip(" .?"), flags=re.IGNORECASE)
        for part in parts
        if len(part.strip().split()) >= 2
    ]
    if len(meaningful) < 2:
        return [question]
    subject_context = meaningful[0]
    return [subject_context] + [f"{subject_context}; {part}" for part in meaningful[1:limit]]


class RAGService:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLMService | None = None,
        settings: Settings | None = None,
    ):
        self.retriever = retriever
        self._llm = llm
        self.settings = settings or get_settings()

    @property
    def llm(self) -> LLMService:
        if self._llm is None:
            self._llm = get_llm_service()
        return self._llm

    def prepare(
        self,
        question: str,
        history: list[dict] | None = None,
        filters: dict[str, str] | None = None,
        rewritten_question: str | None = None,
    ) -> PreparedContext:
        query = rewritten_question or rewrite_query(question, history)
        chunks = self.retriever.retrieve(query, filters=filters)
        terms = query_terms(query)
        # Keep semantic retrieval, but require at least one lexical anchor per chunk so
        # high-scoring yet unrelated documents are not exposed as supporting sources.
        if terms:
            chunks = [item for item in chunks if terms & query_terms(item.chunk.content)]
        evidence_terms = query_terms(" ".join(item.chunk.content for item in chunks))
        coverage = len(terms & evidence_terms) / len(terms) if terms else 0.0
        sufficient = bool(chunks) and coverage >= self.settings.retrieval_min_term_coverage
        if not sufficient:
            chunks = []
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
            evidence_sufficient=sufficient,
            query=query,
        )

    def prepare_multi_step(
        self,
        question: str,
        history: list[dict] | None = None,
        filters: dict[str, str] | None = None,
    ) -> tuple[PreparedContext, list[str]]:
        subqueries = decompose_query(question, self.settings.multi_step_max_subqueries)
        prepared_parts = [self.prepare(query, history, filters, query) for query in subqueries]
        unique: dict[str, RetrievedChunk] = {}
        for part in prepared_parts:
            for chunk in part.chunks:
                unique[chunk.chunk.id] = chunk
        chunks = list(unique.values())[: self.settings.retrieval_top_k * len(subqueries)]
        if not chunks:
            return self.prepare(question, history, filters, question), subqueries
        sources: list[Source] = []
        context_parts: list[str] = []
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
            confidence=max(item.score for item in chunks),
            chunks=chunks,
            evidence_sufficient=all(part.evidence_sufficient for part in prepared_parts),
            query=question,
        ), subqueries

    def generate(
        self,
        question: str,
        prepared: PreparedContext,
        history: list[dict] | None = None,
    ) -> str:
        if not prepared.evidence_sufficient:
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
        prepared = self.prepare(question, history, filters)
        answer = self.generate(question, prepared, history)
        answer, _ = validate_citations(answer, len(prepared.sources))
        return answer, prepared.sources, prepared.confidence
