from langchain_core.tools import StructuredTool

from app.services.prompts import (
    STUDY_PLANNING_PROMPT,
    SUMMARIZATION_PROMPT,
    render_academic_prompt,
)
from app.tools.registry import get_calculator_tool


def test_academic_workflow_has_real_retrieval_generation_and_review_nodes(client):
    response = client.post("/api/chat", json={"question": "What is the attendance policy?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == (
        "I couldn't find information about this in the available college documents."
    )
    assert body["graph_route"] == [
        "analyze_query",
        "rewrite_query",
        "retrieve_information",
        "check_evidence",
        "unknown_response",
        "review_response",
        "finalize_response",
    ]


def test_calculator_is_registered_as_a_langchain_tool(client):
    tool = get_calculator_tool()
    assert isinstance(tool, StructuredTool)
    assert tool.invoke({"expression": "25% of 80"}) == 20
    response = client.post("/api/chat", json={"question": "What is 25% of 80?"})
    assert response.json()["graph_route"] == [
        "analyze_query",
        "select_tool",
        "execute_tool",
        "review_response",
        "finalize_response",
    ]


def test_reusable_prompts_cover_qa_summarization_and_planning():
    qa = render_academic_prompt("When is the exam?", "Source [1] — Calendar")
    summary = SUMMARIZATION_PROMPT.format(context="Source [1] — Rules")
    planning = STUDY_PLANNING_PROMPT.format(
        subjects="DBMS",
        available_hours=2,
        exam_date="2026-06-01",
        constraints="No Saturdays",
    )
    assert "Source [1]" in qa
    assert "Summarize" in summary
    assert "DBMS" in planning and "No Saturdays" in planning


def test_document_upload_runs_ingestion_pipeline(client):
    response = client.post(
        "/api/documents/ingest",
        files={"file": ("faq.txt", b"Registration closes on Friday. " * 30, "text/plain")},
        data={"title": "Student FAQ", "category": "faq", "academic_year": "2025-26"},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["title"] == "Student FAQ"
    assert document["category"] == "faq"
    assert client.get("/api/documents").json()[0]["status"] == "ready"
