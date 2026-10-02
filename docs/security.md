# Security review

- [x] Secrets load from environment variables; `.env` is ignored.
- [x] ORM operations are parameterized.
- [x] Upload extensions and sizes are validated.
- [x] Calculator accepts a restricted AST; arbitrary execution is prohibited.
- [x] LangGraph can route only registered branches/tools.
- [x] Pydantic validates user input.
- [x] Controlled errors hide stack traces and carry request IDs.
- [x] Logs omit API keys and passwords.
- [ ] Add authentication and authorization before an internet-facing deployment (outside MVP scope).
- [ ] Configure TLS, network policies, secret rotation, and managed backups in the deployment platform.
