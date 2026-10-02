# API

- `GET /health`, `GET /health/ready`
- `POST /api/chat` — answer, intent, confidence, and structured sources.
- `POST/GET /api/conversations`, `GET /api/conversations/{id}`
- `POST /api/plans`, `GET/PATCH /api/plans/{id}`
- `GET /api/documents`, `POST /api/documents/ingest`

Interactive OpenAPI documentation is available at `/docs`. Validation failures return HTTP 422, missing resources return 404, and controlled server failures include a request ID without a stack trace.
