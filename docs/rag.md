# RAG and ingestion

Ingestion accepts PDF and UTF-8 TXT, cleans extraction artifacts, removes repeated PDF edge lines, chunks at configurable token estimates, retains page metadata, embeds each chunk, and deduplicates by SHA-256 content hash.

```bash
cd backend
python -m scripts.ingest ../data/raw/academic-regulations.pdf --category regulations --department CSE --academic-year 2026
```

Retrieval uses cosine distance through pgvector in PostgreSQL and supports department, category, and academic-year filters. `RETRIEVAL_TOP_K` and `RETRIEVAL_SCORE_THRESHOLD` control evidence. No qualifying chunk produces the explicit no-evidence response.

Generation uses the Gemini API (`gemini-2.5-flash-lite` by default). Embeddings use the lightweight local `sentence-transformers/all-MiniLM-L6-v2` ONNX model through FastEmbed. Its 384-dimensional vectors match the pgvector column and avoid shipping PyTorch. Each chunk records its embedding model; re-ingesting after a model change replaces incompatible vectors automatically.
