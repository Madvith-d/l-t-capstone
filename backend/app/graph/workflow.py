import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_user
from app.core.config import get_settings
from app.models import StudyPlan, StudySession
from app.planner.engine import PlanValidationError, generate_sessions, validate_sessions
from app.planner.modification import apply_modification, parse_modification
from app.schemas.api import Intent, PlanCreate
from app.services.classification import classify_intent
from app.services.demo import demo_answer, demo_plan_request
from app.services.plans import (
    latest_plan,
    load_plan,
    parse_chat_plan_request,
    session_dicts,
    sync_sessions,
)
from app.services.prompts import UNKNOWN_RESPONSE
from app.services.rag import (
    PreparedContext,
    RAGService,
    decompose_query,
    rewrite_query,
    validate_citations,
)
from app.services.retrieval import Retriever
from app.tools.calculator import CalculatorError
from app.tools.calendar import DatabaseCalendarProvider, parse_calendar_request
from app.tools.registry import get_calculator_tool, get_calendar_tools

logger = logging.getLogger("workflow")


class AssistantState(TypedDict, total=False):
    user_id: str
    conversation_id: str | None
    question: str
    rewritten_question: str | None
    conversation_history: list[dict]
    intent: str
    retrieved_documents: list[dict]
    prepared_context: PreparedContext
    context: str
    evidence_sufficient: bool
    confidence: float
    plan_id: str | None
    plan_request: dict | None
    study_plan: dict | None
    generated_sessions: list[dict]
    plan_instruction: dict | None
    tool_name: str | None
    tool_input: dict | None
    tool_result: dict | None
    tool_calls: list[dict]
    tool_results: list[dict]
    subqueries: list[str]
    demo_answer: str | None
    response: str
    sources: list[dict]
    filters: dict[str, str]
    errors: list[str]
    review_notes: list[str]
    graph_route: list[str]


class AssistantWorkflow:
    def __init__(self, db: Session):
        self.db = db
        self._rag_service: RAGService | None = None
        self.graph = self._build()

    @property
    def rag_service(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = RAGService(Retriever(self.db))
        return self._rag_service

    @staticmethod
    def _path(state: AssistantState, node: str) -> list[str]:
        return state.get("graph_route", []) + [node]

    def _build(self):
        builder = StateGraph(AssistantState)
        nodes = {
            "analyze_query": self.analyze,
            "demo_response": self.demo_response,
            "rewrite_query": self.rewrite,
            "retrieve_information": self.retrieve,
            "check_evidence": self.check_evidence,
            "unknown_response": self.unknown,
            "generate_response": self.generate,
            "validate_citations": self.citations,
            "decompose_request": self.decompose,
            "execute_subtasks": self.execute_subtasks,
            "aggregate_results": self.generate,
            "extract_plan_request": self.extract_plan,
            "generate_plan": self.generate_plan,
            "validate_plan": self.validate_plan,
            "persist_plan": self.persist_plan,
            "load_existing_plan": self.load_existing_plan,
            "parse_modification": self.parse_plan_modification,
            "apply_modification": self.apply_plan_modification,
            "validate_modified_plan": self.validate_plan,
            "persist_modified_plan": self.persist_plan,
            "select_tool": self.select_tool,
            "execute_tool": self.execute_tool,
            "select_calendar_tool": self.select_calendar_tool,
            "execute_calendar_tool": self.execute_calendar_tool,
            "general_response": self.general,
            "review_response": self.review,
            "finalize_response": self.finalize,
        }
        for name, function in nodes.items():
            builder.add_node(name, function)
        builder.add_edge(START, "analyze_query")
        builder.add_conditional_edges(
            "analyze_query",
            self.route,
            {
                "demo": "demo_response",
                "academic": "rewrite_query",
                "multi_step": "decompose_request",
                "planner_create": "extract_plan_request",
                "planner_modify": "load_existing_plan",
                "calculator": "select_tool",
                "calendar": "select_calendar_tool",
                "general": "general_response",
            },
        )
        builder.add_edge("demo_response", "validate_citations")
        builder.add_edge("rewrite_query", "retrieve_information")
        builder.add_edge("retrieve_information", "check_evidence")
        builder.add_conditional_edges(
            "check_evidence",
            lambda state: (
                "unknown"
                if not state.get("evidence_sufficient")
                else "aggregate" if state.get("subqueries") else "generate"
            ),
            {
                "generate": "generate_response",
                "aggregate": "aggregate_results",
                "unknown": "unknown_response",
            },
        )
        builder.add_edge("generate_response", "validate_citations")
        builder.add_edge("decompose_request", "execute_subtasks")
        builder.add_edge("execute_subtasks", "check_evidence")
        builder.add_edge("aggregate_results", "validate_citations")
        builder.add_edge("extract_plan_request", "generate_plan")
        builder.add_edge("generate_plan", "validate_plan")
        builder.add_edge("validate_plan", "persist_plan")
        builder.add_edge("load_existing_plan", "parse_modification")
        builder.add_edge("parse_modification", "apply_modification")
        builder.add_edge("apply_modification", "validate_modified_plan")
        builder.add_edge("validate_modified_plan", "persist_modified_plan")
        builder.add_edge("select_tool", "execute_tool")
        builder.add_edge("select_calendar_tool", "execute_calendar_tool")
        for node in (
            "unknown_response",
            "validate_citations",
            "persist_plan",
            "persist_modified_plan",
            "execute_tool",
            "execute_calendar_tool",
            "general_response",
        ):
            builder.add_edge(node, "review_response")
        builder.add_edge("review_response", "finalize_response")
        builder.add_edge("finalize_response", END)
        return builder.compile()

    def analyze(self, state: AssistantState) -> dict:
        has_plan = bool(latest_plan(self.db, state["user_id"]))
        intent = classify_intent(state["question"], has_plan)
        result: dict = {"intent": intent.value, "graph_route": ["analyze_query"]}
        if get_settings().demo_mode and intent in (
            Intent.ACADEMIC_QA,
            Intent.DOCUMENT_SEARCH,
            Intent.MULTI_STEP,
            Intent.UNKNOWN,
        ):
            answer, sources, confidence = demo_answer(
                state["question"], state.get("conversation_history")
            )
            result.update(
                demo_answer=answer,
                sources=sources,
                confidence=confidence,
                evidence_sufficient=bool(sources),
            )
        return result

    def route(self, state: AssistantState) -> str:
        intent = Intent(state["intent"])
        if state.get("demo_answer") is not None:
            return "demo"
        if intent in (Intent.ACADEMIC_QA, Intent.DOCUMENT_SEARCH, Intent.UNKNOWN):
            return "academic"
        if intent == Intent.MULTI_STEP:
            return "multi_step"
        if intent == Intent.CALCULATION:
            return "calculator"
        if intent == Intent.CALENDAR_ACTION:
            return "calendar"
        if intent == Intent.STUDY_PLAN:
            return "planner_create"
        if intent == Intent.STUDY_PLAN_MODIFICATION:
            return "planner_modify"
        return "general"

    def demo_response(self, state: AssistantState) -> dict:
        return {
            "response": state["demo_answer"],
            "graph_route": self._path(state, "demo_response"),
        }

    def rewrite(self, state: AssistantState) -> dict:
        rewritten = rewrite_query(state["question"], state.get("conversation_history"))
        return {"rewritten_question": rewritten, "graph_route": self._path(state, "rewrite_query")}

    def retrieve(self, state: AssistantState) -> dict:
        prepared = self.rag_service.prepare(
            state["question"],
            state.get("conversation_history"),
            state.get("filters"),
            state.get("rewritten_question"),
        )
        return self._prepared_state(state, prepared, "retrieve_information")

    def _prepared_state(
        self, state: AssistantState, prepared: PreparedContext, node: str
    ) -> dict:
        return {
            "prepared_context": prepared,
            "context": prepared.context,
            "evidence_sufficient": prepared.evidence_sufficient,
            "retrieved_documents": [
                {
                    "chunk_id": item.chunk.id,
                    "document_id": item.document.id,
                    "score": item.score,
                }
                for item in prepared.chunks
            ],
            "sources": [source.model_dump() for source in prepared.sources],
            "confidence": prepared.confidence,
            "graph_route": self._path(state, node),
        }

    def check_evidence(self, state: AssistantState) -> dict:
        return {"graph_route": self._path(state, "check_evidence")}

    def unknown(self, state: AssistantState) -> dict:
        return {
            "response": UNKNOWN_RESPONSE,
            "sources": [],
            "confidence": 0.0,
            "graph_route": self._path(state, "unknown_response"),
        }

    def generate(self, state: AssistantState) -> dict:
        answer = self.rag_service.generate(
            state["question"], state["prepared_context"], state.get("conversation_history")
        )
        node = "aggregate_results" if state.get("subqueries") else "generate_response"
        return {"response": answer, "graph_route": self._path(state, node)}

    def citations(self, state: AssistantState) -> dict:
        answer, notes = validate_citations(state.get("response", ""), len(state.get("sources", [])))
        return {
            "response": answer,
            "review_notes": state.get("review_notes", []) + notes,
            "graph_route": self._path(state, "validate_citations"),
        }

    def decompose(self, state: AssistantState) -> dict:
        subqueries = decompose_query(
            state["question"], self.rag_service.settings.multi_step_max_subqueries
        )
        return {"subqueries": subqueries, "graph_route": self._path(state, "decompose_request")}

    def execute_subtasks(self, state: AssistantState) -> dict:
        prepared, subqueries = self.rag_service.prepare_multi_step(
            state["question"], state.get("conversation_history"), state.get("filters")
        )
        result = self._prepared_state(state, prepared, "execute_subtasks")
        result["subqueries"] = subqueries
        return result

    def extract_plan(self, state: AssistantState) -> dict:
        try:
            payload = (
                demo_plan_request()
                if get_settings().demo_mode
                else PlanCreate.model_validate(state["plan_request"])
                if state.get("plan_request")
                else parse_chat_plan_request(state["question"], state["user_id"])
            )
            payload.user_id = state["user_id"]
            return {
                "plan_request": payload.model_dump(mode="json"),
                "graph_route": self._path(state, "extract_plan_request"),
            }
        except (ValueError, PlanValidationError) as exc:
            errors = exc.errors if isinstance(exc, PlanValidationError) else [str(exc)]
            return {
                "errors": errors,
                "response": "I need valid subjects, an exam date or duration, and daily study hours.",
                "graph_route": self._path(state, "extract_plan_request"),
            }

    def generate_plan(self, state: AssistantState) -> dict:
        if state.get("errors"):
            return {"graph_route": self._path(state, "generate_plan")}
        payload = PlanCreate.model_validate(state["plan_request"])
        try:
            sessions = generate_sessions(payload)
            return {"generated_sessions": sessions, "graph_route": self._path(state, "generate_plan")}
        except PlanValidationError as exc:
            return {"errors": exc.errors, "graph_route": self._path(state, "generate_plan")}

    def validate_plan(self, state: AssistantState) -> dict:
        node = (
            "validate_modified_plan"
            if state.get("intent") == Intent.STUDY_PLAN_MODIFICATION.value
            else "validate_plan"
        )
        if state.get("errors"):
            return {"graph_route": self._path(state, node)}
        if state["intent"] == Intent.STUDY_PLAN.value:
            payload = PlanCreate.model_validate(state["plan_request"])
            subjects = [item.model_dump() for item in payload.subjects]
            exam_date = payload.exam_date
            daily_hours = payload.available_hours_per_day
        else:
            plan = state["study_plan"]
            subjects = plan["subjects"]
            exam_date = plan["exam_date"]
            daily_hours = plan["available_hours_per_day"]
        errors = validate_sessions(state["generated_sessions"], subjects, exam_date, daily_hours)
        return {"errors": errors, "graph_route": self._path(state, node)}

    def persist_plan(self, state: AssistantState) -> dict:
        node = (
            "persist_modified_plan"
            if state.get("intent") == Intent.STUDY_PLAN_MODIFICATION.value
            else "persist_plan"
        )
        if state.get("errors"):
            return {
                "response": "The study plan could not be completed: " + "; ".join(state["errors"]),
                "graph_route": self._path(state, node),
            }
        ensure_user(self.db, state["user_id"])
        if state["intent"] == Intent.STUDY_PLAN.value:
            payload = PlanCreate.model_validate(state["plan_request"])
            plan = StudyPlan(
                user_id=state["user_id"],
                title=payload.title,
                exam_date=payload.exam_date,
                available_hours_per_day=payload.available_hours_per_day,
                subjects=[item.model_dump() for item in payload.subjects],
                constraints={"preferred_times": payload.preferred_times},
            )
            self.db.add(plan)
            self.db.flush()
            for item in state["generated_sessions"]:
                self.db.add(StudySession(plan_id=plan.id, **item))
            action = "created"
        else:
            plan = load_plan(self.db, state["user_id"], state["plan_id"])
            if plan is None:
                return {
                    "response": "No study plan was found for this session.",
                    "graph_route": self._path(state, "persist_plan"),
                }
            sync_sessions(self.db, plan, state["generated_sessions"])
            plan.version += 1
            plan.constraints = {
                **plan.constraints,
                "last_instruction": state["question"],
                "last_command": state["plan_instruction"],
            }
            action = "updated"
        self.db.flush()
        plan = load_plan(self.db, state["user_id"], plan.id) or plan
        plan_data = {
            "id": plan.id,
            "version": plan.version,
            "exam_date": plan.exam_date.isoformat(),
            "sessions": len(plan.sessions),
        }
        node = "persist_modified_plan" if action == "updated" else "persist_plan"
        return {
            "plan_id": plan.id,
            "study_plan": plan_data,
            "tool_results": [{"tool": "study_planner", "action": action, "plan": plan_data}],
            "response": f"Study plan {action}: {len(plan.sessions)} sessions before {plan.exam_date}.",
            "graph_route": self._path(state, node),
        }

    def load_existing_plan(self, state: AssistantState) -> dict:
        plan = (
            load_plan(self.db, state["user_id"], state["plan_id"])
            if state.get("plan_id")
            else latest_plan(self.db, state["user_id"])
        )
        if plan is None:
            return {
                "errors": ["No study plan exists for this session"],
                "response": "No study plan exists yet. Create a plan before requesting changes.",
                "graph_route": self._path(state, "load_existing_plan"),
            }
        return {
            "plan_id": plan.id,
            "study_plan": {
                "subjects": plan.subjects,
                "exam_date": plan.exam_date,
                "available_hours_per_day": plan.available_hours_per_day,
            },
            "generated_sessions": session_dicts(plan),
            "graph_route": self._path(state, "load_existing_plan"),
        }

    def parse_plan_modification(self, state: AssistantState) -> dict:
        if state.get("errors"):
            return {"graph_route": self._path(state, "parse_modification")}
        try:
            command = parse_modification(state["question"], state["study_plan"]["subjects"])
            return {
                "plan_instruction": command.model_dump(mode="json"),
                "graph_route": self._path(state, "parse_modification"),
            }
        except PlanValidationError as exc:
            return {"errors": exc.errors, "graph_route": self._path(state, "parse_modification")}

    def apply_plan_modification(self, state: AssistantState) -> dict:
        if state.get("errors"):
            return {"graph_route": self._path(state, "apply_modification")}
        from app.planner.modification import ModificationCommand

        plan = state["study_plan"]
        try:
            sessions = apply_modification(
                state["generated_sessions"],
                ModificationCommand.model_validate(state["plan_instruction"]),
                plan["subjects"],
                plan["exam_date"],
                plan["available_hours_per_day"],
            )
            return {
                "generated_sessions": sessions,
                "graph_route": self._path(state, "apply_modification"),
            }
        except PlanValidationError as exc:
            return {"errors": exc.errors, "graph_route": self._path(state, "apply_modification")}

    def select_tool(self, state: AssistantState) -> dict:
        return {
            "tool_name": "calculator",
            "tool_input": {"expression": state["question"]},
            "graph_route": self._path(state, "select_tool"),
        }

    def execute_tool(self, state: AssistantState) -> dict:
        try:
            result = get_calculator_tool().invoke(state["tool_input"])
            rendered = int(result) if result.is_integer() else result
            return {
                "response": f"The result is {rendered}.",
                "tool_calls": [{"tool": "calculator", "input": state["tool_input"]}],
                "tool_results": [{"tool": "calculator", "result": rendered}],
                "graph_route": self._path(state, "execute_tool"),
            }
        except (CalculatorError, ValueError) as exc:
            return {
                "response": str(exc),
                "tool_results": [{"tool": "calculator", "error": str(exc)}],
                "graph_route": self._path(state, "execute_tool"),
            }

    def select_calendar_tool(self, state: AssistantState) -> dict:
        try:
            tool_input = parse_calendar_request(state["question"])
            return {
                "tool_name": (
                    "calendar_create_event"
                    if tool_input["operation"] == "create"
                    else "calendar_list_events"
                ),
                "tool_input": tool_input,
                "graph_route": self._path(state, "select_calendar_tool"),
            }
        except ValueError as exc:
            return {
                "errors": [str(exc)],
                "response": str(exc),
                "graph_route": self._path(state, "select_calendar_tool"),
            }

    def execute_calendar_tool(self, state: AssistantState) -> dict:
        if state.get("errors"):
            return {"graph_route": self._path(state, "execute_calendar_tool")}
        ensure_user(self.db, state["user_id"])
        provider = DatabaseCalendarProvider(self.db, state["user_id"])
        tools = {tool.name: tool for tool in get_calendar_tools(provider)}
        operation = state["tool_input"].pop("operation")
        name = "calendar_create_event" if operation == "create" else "calendar_list_events"
        result = tools[name].invoke(state["tool_input"])
        serialized = (
            [event.__dict__ for event in result]
            if isinstance(result, list)
            else result.__dict__
        )
        response = (
            f"Calendar event created for {result.starts_at.isoformat()}."
            if operation == "create"
            else f"You have {len(result)} calendar events."
        )
        return {
            "response": response,
            "tool_results": [{"tool": name, "result": serialized}],
            "graph_route": self._path(state, "execute_calendar_tool"),
        }

    def general(self, state: AssistantState) -> dict:
        return {
            "response": "Hello. Ask about an academic document, calculate a value, manage a study plan, or schedule a calendar event.",
            "graph_route": self._path(state, "general_response"),
        }

    def review(self, state: AssistantState) -> dict:
        response = state.get("response", "").strip()
        notes = state.get("review_notes", [])
        intent = Intent(state["intent"])
        if intent in (Intent.ACADEMIC_QA, Intent.DOCUMENT_SEARCH, Intent.UNKNOWN, Intent.MULTI_STEP):
            if not state.get("evidence_sufficient") or not state.get("sources"):
                response = UNKNOWN_RESPONSE
                notes.append("withheld_academic_answer_without_sufficient_evidence")
            elif response == UNKNOWN_RESPONSE:
                notes.append("model_declined_despite_retrieved_evidence")
                return {
                    "response": response,
                    "sources": [],
                    "confidence": 0.0,
                    "review_notes": notes,
                    "graph_route": self._path(state, "review_response"),
                }
        elif not response:
            response = "I couldn't complete that request. Please provide more detail."
            notes.append("replaced_empty_response")
        return {
            "response": response,
            "review_notes": notes,
            "graph_route": self._path(state, "review_response"),
        }

    def finalize(self, state: AssistantState) -> dict:
        logger.info(
            "intent=%s graph_route=%s confidence=%.3f tools=%s errors=%s",
            state.get("intent"),
            state.get("graph_route"),
            state.get("confidence", 0),
            state.get("tool_calls", []),
            state.get("errors", []),
        )
        return {
            "sources": state.get("sources", []),
            "tool_results": state.get("tool_results", []),
            "confidence": state.get("confidence", 0),
            "graph_route": self._path(state, "finalize_response"),
        }

    def invoke(self, state: AssistantState) -> AssistantState:
        return self.graph.invoke(state)
