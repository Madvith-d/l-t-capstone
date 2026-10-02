# Baseline versus RAG evaluation

`evaluation/dataset.json` contains direct, retrieval, follow-up, unknown, and multi-step questions. Run from `backend/`:

```bash
python -m scripts.evaluate
```

The script sends identical questions to the configured baseline and RAG paths and writes `evaluation/results.json`. It records answers, sources, confidence, and review fields. Correctness and relevance remain nullable for a human or external evaluator; no superiority claim is hard-coded. Report correctness, grounding, unsupported-answer rate, relevance, and follow-up handling only after completing those annotations.
