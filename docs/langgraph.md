# LangGraph

`backend/app/graph/workflow.py` defines structured `AssistantState` and an inspectable compiled graph. `analyze_query` classifies into the controlled intent enum, then conditional edges route academic, planner, tool, and general branches.

The academic branch uses real, separate `retrieve_information`, `generate_response`, and `review_response` nodes. The review node withholds an academic answer when retrieval returned no source evidence. Tool and other branches also pass through review before `finalize_response`. The API exposes `graph_route`, making the executed path testable and visible during evaluation.

The calculator is registered as a LangChain `StructuredTool`, but tool selection remains explicit in LangGraph. Reusable LangChain templates for academic Q&A, source-preserving summarization, and study planning are defined in `backend/app/services/prompts.py`.

The planner API intentionally runs deterministic generation/validation outside free-form chat. This keeps dates, durations, coverage, and daily limits enforceable while still allowing natural-language plan modifications.
