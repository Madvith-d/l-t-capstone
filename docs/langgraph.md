# LangGraph

`backend/app/graph/workflow.py` defines structured `AssistantState` and a bounded compiled graph. `analyze_query` classifies into the controlled intent enum and routes explicitly.

## Branches

```text
academic: rewrite_query → retrieve_information → check_evidence
          → unknown_response OR generate_response → validate_citations
multi:    decompose_request → execute_subtasks → check_evidence
          → aggregate_results → validate_citations
planner:  extract_plan_request → generate_plan → validate_plan → persist_plan
modify:   load_existing_plan → parse_modification → apply_modification
          → validate_modified_plan → persist_modified_plan
tools:    select_tool/select_calendar_tool → execute tool
general:  general_response
all:      review_response → finalize_response
```

The evidence check combines the configured vector threshold with query-term coverage. An insufficient branch returns the exact unknown response with no sources. Citation validation removes markers that do not map to the authoritative structured source list and adds a valid marker when a grounded answer omitted one.

Multi-step decomposition is capped by `MULTI_STEP_MAX_SUBQUERIES`; there is no autonomous loop. Planner mutation is deterministic after structured instruction parsing. The database—not graph memory—is the source of truth for the current user’s plan.

The calculator and persistent mock calendar are registered as LangChain `StructuredTool` instances. Reusable LangChain prompts for academic Q&A, source-preserving summarization, and study planning live in `backend/app/services/prompts.py`. The API returns `graph_route` for diagnostics and acceptance testing.
