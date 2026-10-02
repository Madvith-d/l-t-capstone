# Northstar — College Academic Assistant

A production-structured MVP that answers from college documents, keeps conversation context, creates and modifies validated study plans, and executes a restricted calculator through an explicit LangGraph workflow.

## Architecture and stack

Next.js 16 + TypeScript frontend; FastAPI + Pydantic backend; LangChain/LangGraph orchestration; Gemini 2.5 Flash Lite generation; lightweight FastEmbed MiniLM embeddings; SQLAlchemy/Alembic; PostgreSQL 16 + pgvector. Provider-specific LLM and embedding clients are isolated behind interfaces. See [architecture](docs/architecture.md).

## Prerequisites

Docker 24+ with Compose, or Node 22+ and Python 3.11–3.13 with PostgreSQL/pgvector.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open the UI at <http://localhost:3000>, API documentation at <http://localhost:8000/docs>, and health endpoint at <http://localhost:8000/health>.

## Configuration

Important variables: `DATABASE_URL`, `GEMINI_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `RETRIEVAL_TOP_K`, `RETRIEVAL_SCORE_THRESHOLD`, `CHUNK_SIZE_TOKENS`, and `CHUNK_OVERLAP_TOKENS`. Generation defaults to Gemini 2.5 Flash Lite. Embeddings default to the local 384-dimensional `sentence-transformers/all-MiniLM-L6-v2` model through FastEmbed, so no embedding API key or PyTorch installation is required.

## Documents

Place approved PDF/TXT files in `data/raw`, then:

```bash
docker compose exec backend python -m scripts.ingest data/raw/academic-regulations.pdf --category regulations
```

Content hashes make repeated ingestion idempotent. PDF chunks retain page numbers and source metadata. See [RAG documentation](docs/rag.md).

## Development and tests

See [setup](docs/setup.md). Typical checks:

```bash
cd backend && pytest
cd frontend && npm run build
```

The API is documented in [docs/api.md](docs/api.md), workflow in [docs/langgraph.md](docs/langgraph.md), and evaluation in [docs/evaluation.md](docs/evaluation.md).

## Evaluation

From `backend/`, run `python -m scripts.evaluate` after ingesting representative college documents. The output compares the same dataset against baseline and RAG paths without hard-coded claims.

## Scope and safety

The MVP never invents missing college evidence, uses a restricted calculator rather than code execution, validates every plan deterministically, and keeps real calendar integration, auth administration, notifications, OCR, and background workers out of scope. Review [scope.md](scope.md) and [security checklist](docs/security.md).
