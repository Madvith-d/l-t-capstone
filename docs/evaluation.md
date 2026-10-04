# Baseline versus RAG evaluation

`evaluation/dataset.json` contains direct, retrieval, follow-up, unknown, and multi-step questions. The same questions go to both paths, but the prompts are intentionally different:

- **Baseline:** a normal general-purpose assistant with no claim of access to private college documents.
- **RAG:** college-specific claims must come only from retrieved evidence.

Run natively from any working directory:

```bash
cd backend
python -m scripts.evaluate
```

Or in Compose, where `evaluation/` is mounted at `/app/evaluation`:

```bash
docker compose exec backend python -m scripts.evaluate
```

The script writes `evaluation/results.json` and `evaluation/summary.json`. Per-question output includes baseline/RAG answers, sources, confidence, measured correctness where an expected value is available, grounding, lexical relevance, follow-up handling, and an unsupported-answer indicator. Summary output reports measured correctness, grounding rate, unsupported-answer rate, and mean relevance. Nullable correctness remains honest for questions without an approved expected answer; the report does not hard-code a claim that RAG is superior.
