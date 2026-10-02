# LangGraph

`backend/app/graph/workflow.py` defines structured `AssistantState` and an inspectable compiled graph. `analyze_query` classifies into the controlled intent enum, then conditional edges route academic, planner, tool, and general branches. Every branch reaches `finalize_response`, which normalizes output and logs the graph path.

The planner API intentionally runs deterministic generation/validation outside free-form chat. This keeps dates, durations, coverage, and daily limits enforceable.
