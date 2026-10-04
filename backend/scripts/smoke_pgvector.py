"""Production-like PostgreSQL/pgvector smoke test. Run inside the backend container."""

from pathlib import Path

from sqlalchemy import func, select, text

from app.db.session import SessionLocal
from app.models import DocumentChunk
from app.services.ingestion import IngestionService
from app.services.retrieval import Retriever


def run() -> None:
    path = Path("/app/data/demo/DEMO-academic-regulations.txt")
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "data/demo/DEMO-academic-regulations.txt"
    with SessionLocal() as db:
        if db.bind is None or db.bind.dialect.name != "postgresql":
            raise RuntimeError("This smoke test requires PostgreSQL with pgvector")
        extension = db.scalar(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
        if extension != "vector":
            raise RuntimeError("pgvector extension is not installed")
        document, _ = IngestionService(db).ingest(
            path,
            {
                "title": "Synthetic Demo Academic Regulations",
                "category": "demo",
                "academic_year": "DEMO",
                "source": str(path),
            },
        )
        count = db.scalar(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document.id)
        )
        if not count:
            raise RuntimeError("Ingestion produced no chunks")
        results = Retriever(db).retrieve("minimum attendance requirement")
        demo_result = next((item for item in results if item.document.id == document.id), None)
        if demo_result is None:
            raise RuntimeError("pgvector retrieval did not return the demo regulations source")
        print(
            f"PASS: vector extension, {count} chunks, demo source retrieved, "
            f"score={demo_result.score:.3f}"
        )


if __name__ == "__main__":
    run()
