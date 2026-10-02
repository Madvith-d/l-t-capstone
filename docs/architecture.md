# Architecture

```text
Next.js UI → FastAPI routes → application services → LangGraph
                                             ├─ RAG → embeddings → pgvector
                                             ├─ deterministic planner
                                             └─ restricted tools
```

The API layer validates transport schemas and delegates behavior. `AssistantWorkflow` owns explicit intent routing. RAG, ingestion, providers, tools, and planning remain independent modules. Gemini 2.5 Flash Lite handles generation, while FastEmbed runs the 384-dimensional MiniLM embedding model locally on CPU. SQLAlchemy is the persistence boundary; PostgreSQL uses pgvector while SQLite JSON vectors support unit tests.

## LangGraph routes

- Academic/document/unknown: analyze → retrieve → validate context → answer → finalize.
- Calculation: analyze → select calculator → execute → finalize.
- Planner requests: analyze → planner response → finalize. Structured plan creation/modification uses dedicated APIs so deterministic constraints remain authoritative.

No arbitrary tool or code execution is exposed.
