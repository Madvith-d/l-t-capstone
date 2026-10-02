from pathlib import Path

from app.services.embeddings import LocalEmbeddingService
from app.services.ingestion import IngestionService, PageText, chunk_pages, clean_text
from app.services.llm import LocalLLMService


def test_clean_and_chunk_preserves_page_metadata():
    cleaned = clean_text("Attendance   requirement\n\n\n85 percent")
    chunks = chunk_pages(
        [PageText(14, cleaned)], size=100, overlap=10, default_section="Attendance"
    )
    assert "Attendance requirement" in chunks[0].content
    assert chunks[0].page_number == 14
    assert chunks[0].section == "Attendance"


def test_local_answer_keeps_first_evidence_sentence():
    context = "Source [1] — Regulations, page 14:\nStudents must maintain 85 percent attendance."
    answer = LocalLLMService().answer("What is the attendance requirement?", context)
    assert "85 percent" in answer


def test_duplicate_document_is_not_reingested(db, tmp_path: Path):
    path = tmp_path / "rules.txt"
    path.write_text("The attendance requirement is 85 percent. " * 30)
    service = IngestionService(db, LocalEmbeddingService())
    first, created = service.ingest(path, {"category": "regulations"})
    second, created_again = service.ingest(path, {"category": "regulations"})
    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert len(first.chunks) > 0
