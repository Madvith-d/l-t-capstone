# Security review

- [x] Secrets load from environment variables; `.env` is ignored and not tracked.
- [x] ORM operations are parameterized.
- [x] Upload extension, size, PDF signature, and non-empty extracted text are validated.
- [x] Calculator uses a restricted AST; no `eval`, `exec`, shell, or subprocess execution exists.
- [x] LangGraph can route only registered calculator/calendar tools.
- [x] Pydantic validates transport and structured modification input.
- [x] Controlled errors hide stack traces and carry request IDs.
- [x] Logs omit API keys and passwords.
- [x] Conversations, plans, and calendar events are owner-scoped by stable anonymous `X-User-ID`.
- [x] Identical document content updates metadata without duplicating vectors.
- [ ] Anonymous IDs provide isolation but not authentication. Add authenticated identity before internet-facing deployment.
- [ ] Configure TLS, network policy, rate limiting, secret rotation, and managed backups in the deployment platform.
