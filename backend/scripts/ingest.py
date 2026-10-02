import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.ingestion import IngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDF/TXT academic documents")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--category")
    parser.add_argument("--department")
    parser.add_argument("--academic-year")
    args = parser.parse_args()
    with SessionLocal() as db:
        service = IngestionService(db)
        for path in args.paths:
            document, created = service.ingest(
                path,
                {
                    "category": args.category,
                    "department": args.department,
                    "academic_year": args.academic_year,
                },
            )
            print(
                f"{'ingested' if created else 'skipped duplicate'}: {document.title} ({document.id})"
            )


if __name__ == "__main__":
    main()
