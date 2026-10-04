# Architecture

```text
Next.js UI → FastAPI routes → application services → LangGraph
                                             ├─ RAG → FastEmbed → pgvector
                                             ├─ deterministic planner → PostgreSQL
                                             └─ registered calculator/calendar tools
```

The configured default generator is the host Ollama service using `gemma4:e2b`; the backend container reaches the loopback-only daemon through a lightweight TCP bridge without duplicating the model in Docker. Gemini and deterministic local providers remain isolated alternatives.

The API validates transport schemas and requires a stable anonymous `X-User-ID` for user-owned resources. This is not full authentication, but conversations, plans, and mock calendar events are always queried by both resource ID and owner ID. The browser stores this opaque ID in local storage.

`AssistantWorkflow` owns bounded routing. Provider, retrieval, ingestion, planning, modification, and tool logic remain separate modules. SQLAlchemy is the persistence boundary; PostgreSQL uses pgvector while SQLite JSON vectors remain available for fast unit tests.

## LangGraph routes

- Academic: analyze → rewrite → retrieve → evidence check → generate/no-evidence → citation validation → review → finalize.
- Multi-step: analyze → bounded decomposition → retrieve subtasks → aggregate → citation validation → review → finalize.
- Planner creation: analyze → extract → generate → validate → persist → review → finalize.
- Planner modification: analyze → owner-scoped plan load → structured modification parse → deterministic apply → validate → in-place persistence → review → finalize.
- Calculator/calendar: analyze → select registered tool → execute → review → finalize.

The mock calendar persists events in PostgreSQL and follows a provider interface that can later be replaced. No arbitrary tool or code execution is exposed.
