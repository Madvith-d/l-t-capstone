# Cross-stack tests

Fast unit/API tests live in `backend/tests` and use SQLite plus deterministic local providers. They cover ingestion, evidence gating, citations, query rewriting, classification, tools, owner isolation, planner validation, stable in-place modification, and LangGraph scenario routes.

Production-like PostgreSQL/pgvector smoke path:

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.smoke_pgvector
```

The smoke script requires PostgreSQL, verifies the `vector` extension, ingests a synthetic document with the real FastEmbed provider, confirms stored chunks, performs the pgvector cosine query, and verifies the expected source ranks first. It is intentionally separate from credential-free unit CI.

Frontend gates:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

The final manual/browser scenarios are listed in `phases.md`; the API equivalents are covered in `backend/tests/test_stabilization.py` and were also executed against a fresh Compose project.
