# API

- `GET /health`, `GET /health/ready`
- `POST /api/chat` — answer, intent, confidence, structured sources, tool results, and graph route.
- `POST /api/conversations`
- `GET /api/conversations` — lightweight owner-scoped metadata list.
- `GET /api/conversations/{id}` — owner-scoped conversation with messages.
- `GET /api/plans` — owner-scoped plans, newest first.
- `POST /api/plans`
- `GET/PATCH /api/plans/{id}` — owner-scoped retrieval and in-place modification.
- `GET /api/documents`, `POST /api/documents/ingest`

## Anonymous session identity

User-owned endpoints require an opaque stable `X-User-ID` header containing 8–36 letters, digits, underscores, or hyphens. The frontend creates a UUID once and stores it in browser local storage. A resource ID alone cannot access another identity’s conversation, plan, or calendar event. This provides MVP isolation, not identity verification; production internet deployment still requires authentication.

```bash
curl -H 'X-User-ID: demo-user-0001' http://localhost:8000/api/plans
```

Validation errors return 422, identity failures 401/403, missing or mismatched resources 404, provider failures 503, and controlled server failures 500. Error payloads include a stable code/message where applicable and a request ID without stack traces.

Interactive OpenAPI documentation is available at `/docs`.
