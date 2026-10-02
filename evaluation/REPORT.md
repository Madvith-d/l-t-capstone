# Basic LLM vs RAG Evaluation Report

## Status

The evaluation harness and 19-question dataset are ready. A scored comparison has not been claimed because no owner-approved college corpus or production LLM credentials were supplied.

## Reproduction

1. Ingest representative approved documents.
2. Configure the LLM and embedding providers.
3. From `backend/`, run `python -m scripts.evaluate`.
4. Review `evaluation/results.json` and fill the nullable correctness, relevance, and follow-up fields.
5. Calculate category averages and unsupported-answer rate from the reviewed file.

## Metrics

- Correctness: human score against the approved source material.
- Grounding: whether an answer includes supporting source records.
- Unsupported-answer rate: answers making unsupported claims divided by all answers.
- Relevance: human score for responsiveness to the question.
- Follow-up handling: whether a follow-up is resolved using bounded conversation context.

## Results

Pending an approved evaluation corpus. No assertion that either system performs better is made before measurement.
