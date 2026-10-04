# RAG and ingestion

Ingestion accepts PDF and UTF-8 TXT, cleans extraction artifacts, removes repeated PDF edge lines, chunks at configurable token estimates, retains page metadata, embeds each chunk, and deduplicates by SHA-256 content hash. Empty or image-only PDFs are rejected rather than marked ready. Re-uploading identical bytes with changed metadata updates the document and chunk metadata without duplicating vectors.

```bash
cd backend
python -m scripts.ingest ../data/raw/academic-regulations.pdf --category regulations --department CSE --academic-year 2026
```

## Synthetic demo corpus

`data/demo/` contains clearly labelled fictional documents for development only. They are not official policy and must never be presented as such.

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.ingest \
  data/demo/DEMO-academic-regulations.txt \
  data/demo/DEMO-semester-four-syllabus.txt \
  --category demo --academic-year DEMO
```

Production remains dependent on owner-approved college documents uploaded from the Sources screen or ingested from `data/raw/`.

Retrieval uses cosine distance through pgvector and supports department, category, and academic-year filters. `RETRIEVAL_TOP_K`, `RETRIEVAL_SCORE_THRESHOLD`, and `RETRIEVAL_MIN_TERM_COVERAGE` control evidence sufficiency. No qualifying evidence produces the exact no-evidence response and an empty source list.

Generation uses the configured LLM. Fresh development defaults to the already-installed host Ollama with `gemma4:e2b`. Compose reaches it through a lightweight host TCP bridge at `http://host.docker.internal:11435` and does not install or duplicate the model. Set `OLLAMA_BASE_URL=http://localhost:11434` for native backend development. Gemini and deterministic local fallback providers remain available through configuration. FastEmbed uses the cached 384-dimensional `BAAI/bge-small-en-v1.5` ONNX model, which provides stronger semantic retrieval than the previous MiniLM default while retaining the existing pgvector dimension. Provider instances are process-cached while remaining injectable in tests.

After changing an embedding model, rebuild every stored vector so query and document vectors remain in the same space:

```bash
docker compose exec backend python -m scripts.reembed
```

## PostgreSQL/pgvector smoke test

After starting Compose:

```bash
docker compose exec backend python -m scripts.smoke_pgvector
```

This verifies the vector extension, demo ingestion, stored chunks/embeddings, a real pgvector cosine query, and the expected top source.
