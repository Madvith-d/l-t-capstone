"""Re-embed all stored chunks after changing the configured embedding model."""

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import DocumentChunk
from app.services.embeddings import get_embedding_service

BATCH_SIZE = 64


def run() -> None:
    embeddings = get_embedding_service()
    with SessionLocal() as db:
        chunks = list(db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)).all())
        if not chunks:
            print("No document chunks found. Ingest documents first.")
            return
        try:
            for start in range(0, len(chunks), BATCH_SIZE):
                batch = chunks[start : start + BATCH_SIZE]
                vectors = embeddings.embed_documents([chunk.content for chunk in batch])
                for chunk, vector in zip(batch, vectors, strict=True):
                    if len(vector) != embeddings.dimensions:
                        raise RuntimeError(
                            f"Embedding dimension mismatch: expected {embeddings.dimensions}, "
                            f"received {len(vector)}"
                        )
                    chunk.embedding = vector
                    chunk.metadata_ = {
                        **chunk.metadata_,
                        "embedding_model": embeddings.model_name,
                    }
            db.commit()
        except Exception:
            db.rollback()
            raise
        print(f"Re-embedded {len(chunks)} chunks with {embeddings.model_name}.")


if __name__ == "__main__":
    run()
