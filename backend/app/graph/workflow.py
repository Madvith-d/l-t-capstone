import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.schemas.api import Intent
from app.services.classification import classify_intent
from app.services.rag import RAGService
from app.services.retrieval import Retriever
from app.tools.calculator import CalculatorError, calculate

logger = logging.getLogger("workflow")


class AssistantState(TypedDict, total=False):
    user_id: str | None
    question: str
    conversation_history: list[dict]
    intent: str
    retrieved_documents: list[dict]
    context: str
    tool_calls: list[dict]
    tool_results: list[dict]
    study_plan: dict | None
    response: str
    sources: list[dict]
    confidence: float
    filters: dict[str, str]
    graph_route: list[str]


class AssistantWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self.graph = self._build()

    def _build(self):
        builder = StateGraph(AssistantState)
        builder.add_node("analyze_query", self.analyze)
        builder.add_node("retrieve_documents", self.academic)
        builder.add_node("execute_tool", self.tool)
        builder.add_node("planner_response", self.planner)
        builder.add_node("general_response", self.general)
        builder.add_node("finalize_response", self.finalize)
        builder.add_edge(START, "analyze_query")
        builder.add_conditional_edges(
            "analyze_query",
            self.route,
            {
                "academic": "retrieve_documents",
                "tool": "execute_tool",
                "planner": "planner_response",
                "general": "general_response",
            },
        )
        for node in ("retrieve_documents", "execute_tool", "planner_response", "general_response"):
            builder.add_edge(node, "finalize_response")
        builder.add_edge("finalize_response", END)
        return builder.compile()

    def analyze(self, state: AssistantState) -> dict:
        intent = classify_intent(state["question"], bool(state.get("study_plan")))
        return {"intent": intent.value, "graph_route": ["analyze_query"]}

    def route(self, state: AssistantState) -> str:
        intent = Intent(state["intent"])
        if intent in (Intent.ACADEMIC_QA, Intent.DOCUMENT_SEARCH, Intent.UNKNOWN):
            return "academic"
        if intent == Intent.CALCULATION:
            return "tool"
        if intent in (Intent.STUDY_PLAN, Intent.STUDY_PLAN_MODIFICATION):
            return "planner"
        return "general"

    def academic(self, state: AssistantState) -> dict:
        answer, sources, confidence = RAGService(Retriever(self.db)).answer(
            state["question"], state.get("conversation_history"), state.get("filters")
        )
        return {
            "response": answer,
            "sources": [source.model_dump() for source in sources],
            "confidence": confidence,
            "graph_route": state["graph_route"]
            + ["retrieve_documents", "validate_context", "generate_answer"],
        }

    def tool(self, state: AssistantState) -> dict:
        try:
            result = calculate(state["question"])
            rendered = int(result) if result.is_integer() else result
            return {
                "response": f"The result is {rendered}.",
                "tool_calls": [{"tool": "calculator", "input": state["question"]}],
                "tool_results": [{"tool": "calculator", "result": rendered}],
                "graph_route": state["graph_route"] + ["select_tool", "execute_tool"],
            }
        except CalculatorError as exc:
            return {
                "response": str(exc),
                "tool_results": [{"tool": "calculator", "error": str(exc)}],
            }

    def planner(self, state: AssistantState) -> dict:
        message = "Use the Study planner to provide subjects, topics, exam date, and available daily hours."
        if state["intent"] == Intent.STUDY_PLAN_MODIFICATION.value:
            message = "Open the saved plan and enter this instruction in its modification field."
        return {"response": message, "graph_route": state["graph_route"] + ["planner_response"]}

    def general(self, state: AssistantState) -> dict:
        return {
            "response": "Hello. Ask about an academic document, calculate a value, or create a study plan.",
            "graph_route": state["graph_route"] + ["general_response"],
        }

    def finalize(self, state: AssistantState) -> dict:
        logger.info(
            "intent=%s graph_route=%s confidence=%.3f",
            state.get("intent"),
            state.get("graph_route"),
            state.get("confidence", 0),
        )
        return {
            "sources": state.get("sources", []),
            "tool_results": state.get("tool_results", []),
            "confidence": state.get("confidence", 0),
            "graph_route": state.get("graph_route", []) + ["finalize_response"],
        }

    def invoke(self, state: AssistantState) -> AssistantState:
        return self.graph.invoke(state)
