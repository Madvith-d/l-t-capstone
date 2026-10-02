import math
from dataclasses import dataclass

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, cast, literal, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import Document, DocumentChunk
from app.services.embeddings import EmbeddingService, get_embedding_service


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    document: Document
    score: float


def cosine(a: list[float], b: list[float]) -> float:
    denominator = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b)) / denominator if denominator else 0.0


class Retriever:
    def __init__(
        self,
        db: Session,
        embeddings: EmbeddingService | None = None,
        settings: Settings | None = None,
    ):
        self.db = db
        self.settings = settings or get_settings()
        self.embeddings = embeddings or get_embedding_service(self.settings)

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        filters: dict[str, str] | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k or self.settings.retrieval_top_k
        threshold = (
            self.settings.retrieval_score_threshold if score_threshold is None else score_threshold
        )
        filters = filters or {}
        vector = self.embeddings.embed_query(query)
        statement = select(DocumentChunk, Document).join(Document)
        for field in ("department", "category", "academic_year"):
            if value := filters.get(field):
                statement = statement.where(getattr(Document, field) == value)
        if self.db.bind and self.db.bind.dialect.name == "postgresql":
            query_vector = literal(vector, type_=Vector(self.settings.embedding_dimension))
            distance = cast(DocumentChunk.embedding.op("<=>")(query_vector), Float)
            rows = self.db.execute(
                statement.add_columns(distance.label("distance")).order_by(distance).limit(top_k)
            ).all()
            found = [RetrievedChunk(row[0], row[1], max(0.0, 1.0 - float(row[2]))) for row in rows]
        else:
            rows = self.db.execute(statement).all()
            found = sorted(
                [
                    RetrievedChunk(chunk, document, cosine(vector, chunk.embedding))
                    for chunk, document in rows
                ],
                key=lambda item: item.score,
                reverse=True,
            )[:top_k]
        return [item for item in found if item.score >= threshold]
