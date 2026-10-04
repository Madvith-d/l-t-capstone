# Basic LLM vs RAG Evaluation Report

## Status

The reproducible 19-question harness covers direct, retrieval, follow-up, unknown, and multi-step questions. Baseline and RAG use separate prompts. The synthetic demo corpus provides expected text for six questions; unknown questions are scored against the required no-evidence response. Questions without an approved expected answer retain nullable correctness rather than receiving invented labels.

## Reproduction

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.ingest \
  data/demo/DEMO-academic-regulations.txt \
  data/demo/DEMO-semester-four-syllabus.txt \
  --category demo --academic-year DEMO
docker compose exec backend python -m scripts.evaluate
```

Outputs are `evaluation/results.json` and `evaluation/summary.json` (generated files are ignored by Git).

## Measured fields

- Correctness when `expected_contains` is provided, plus exact safe handling for unknown questions.
- Grounding: structured sources and a valid citation marker.
- Unsupported-answer indicator: a non-no-evidence answer without sources.
- Lexical relevance.
- Follow-up handling when a follow-up returns grounded evidence.

## Latest verified development run

On 2026-10-04, the local provider against the active development corpus completed all 19 questions and reported:

- measured correctness: `1.0` among questions with an expected result;
- grounding rate: `0.6842`;
- unsupported-answer rate: `0.0`;
- mean lexical relevance: `0.4089`.

This run verifies the harness, not model superiority. Re-run against the owner-approved production corpus and configured provider before reporting production quality.
