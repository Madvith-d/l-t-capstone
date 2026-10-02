from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Document
from app.schemas.api import DocumentOut
from app.services.ingestion import SUPPORTED_EXTENSIONS, IngestionService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return list(db.scalars(select(Document).order_by(Document.created_at.desc())).all())


@router.post("/ingest", response_model=DocumentOut, status_code=201)
async def ingest_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str | None = Form(None),
    department: str | None = Form(None),
    academic_year: str | None = Form(None),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PDF and TXT documents are supported")
    content = await file.read()
    if len(content) > get_settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document exceeds the configured upload limit")
    with NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
        temporary.write(content)
        path = Path(temporary.name)
    try:
        document, _ = IngestionService(db).ingest(
            path,
            {
                "title": title or Path(file.filename or "document").stem,
                "category": category,
                "department": department,
                "academic_year": academic_year,
                "source": file.filename,
            },
        )
        document.source = file.filename or document.source
        db.commit()
        db.refresh(document)
        return document
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)
