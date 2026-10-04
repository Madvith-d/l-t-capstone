from datetime import date, timedelta
from pathlib import Path

from app.models import StudySession
from app.services.embeddings import LocalEmbeddingService
from app.services.ingestion import IngestionService
from app.services.rag import decompose_query, rewrite_query, validate_citations


def test_query_rewrite_uses_only_relevant_latest_user_turn():
    history = [
        {"role": "user", "content": "Tell me about DBMS."},
        {"role": "assistant", "content": "DBMS details."},
        {"role": "user", "content": "What is the attendance requirement?"},
        {"role": "assistant", "content": "It is in the policy."},
    ]
    rewritten = rewrite_query("What happens if I don't meet it?", history)
    assert "attendance requirement" in rewritten
    assert "DBMS" not in rewritten


def test_citation_validation_removes_invalid_and_repairs_missing_markers():
    cleaned, notes = validate_citations("Use policy [1], not [9].", 2)
    assert "[1]" in cleaned and "[9]" not in cleaned
    assert "removed_invalid_citation_9" in notes
    repaired, notes = validate_citations("Grounded answer.", 1)
    assert repaired.endswith("[1]")
    assert "added_authoritative_source_marker_1" in notes
    unknown, notes = validate_citations(
        "I couldn't find information about this in the available college documents.", 1
    )
    assert unknown.endswith("documents.") and "[1]" not in unknown
    assert "normalized_model_no_evidence_response" in notes


def test_multi_step_decomposition_is_bounded():
    parts = decompose_query(
        "Find semester 4 subjects and identify practical courses and list assessments and deadlines",
        limit=3,
    )
    assert len(parts) == 3
    assert all("semester 4" in part for part in parts)


def test_empty_document_is_rejected(db, tmp_path: Path):
    path = tmp_path / "empty.txt"
    path.write_text("  \n\n")
    service = IngestionService(db, LocalEmbeddingService())
    try:
        service.ingest(path)
    except ValueError as exc:
        assert "no searchable text" in str(exc)
    else:
        raise AssertionError("Expected empty document rejection")


def test_duplicate_content_updates_metadata(db, tmp_path: Path):
    path = tmp_path / "rules.txt"
    path.write_text("Attendance policy and examination eligibility. " * 30)
    service = IngestionService(db, LocalEmbeddingService())
    first, created = service.ingest(path, {"title": "Old title", "category": "rules"})
    second, created_again = service.ingest(path, {"title": "New title", "category": "policy"})
    assert created and not created_again
    assert first.id == second.id
    assert second.title == "New title"
    assert second.category == "policy"
    assert second.chunks[0].metadata_["title"] == "New title"


def test_conversations_are_owner_scoped(client):
    created = client.post("/api/chat", json={"question": "Hello"}).json()
    conversation_id = created["conversation_id"]
    assert client.get(f"/api/conversations/{conversation_id}").status_code == 200
    other_headers = {"X-User-ID": "other-user-0002"}
    assert client.get(
        f"/api/conversations/{conversation_id}", headers=other_headers
    ).status_code == 404
    assert all(
        item["id"] != conversation_id
        for item in client.get("/api/conversations", headers=other_headers).json()
    )


def test_resources_are_owner_scoped_and_plan_patch_preserves_session_ids(client, db):
    plan_response = client.post(
        "/api/plans",
        json={
            "subjects": [{"name": "DBMS", "topics": ["SQL", "Transactions"], "difficulty": 4}],
            "exam_date": (date.today() + timedelta(days=20)).isoformat(),
            "available_hours_per_day": 2,
        },
    )
    assert plan_response.status_code == 201
    plan = plan_response.json()
    original = {item["id"]: item for item in plan["sessions"]}
    changed = client.patch(
        f"/api/plans/{plan['id']}", json={"instruction": "I cannot study on Saturday"}
    )
    assert changed.status_code == 200
    updated = changed.json()
    assert updated["version"] == 2
    assert {item["id"] for item in updated["sessions"]} == set(original)
    for item in updated["sessions"]:
        assert item["status"] == original[item["id"]]["status"]
    assert db.query(StudySession).count() == len(original)

    other_headers = {"X-User-ID": "other-user-0002"}
    assert client.get(f"/api/plans/{plan['id']}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/plans/{plan['id']}",
        headers=other_headers,
        json={"instruction": "I cannot study on Saturday"},
    ).status_code == 404


def test_rag_follow_up_unknown_and_multi_step_scenarios(client, db):
    service = IngestionService(db, LocalEmbeddingService())
    for name in ("DEMO-academic-regulations.txt", "DEMO-semester-four-syllabus.txt"):
        service.ingest(
            Path("../data/demo") / name,
            {"title": name, "category": "demo", "academic_year": "DEMO"},
        )
    direct = client.post(
        "/api/chat", json={"question": "What is the attendance requirement?"}
    ).json()
    assert direct["sources"] and "85 percent" in direct["answer"]
    follow_up = client.post(
        "/api/chat",
        json={
            "conversation_id": direct["conversation_id"],
            "question": "What happens if I do not meet it?",
        },
    ).json()
    assert follow_up["sources"] and "ineligible" in follow_up["answer"]
    unknown = client.post(
        "/api/chat", json={"question": "What will the cafeteria serve next Tuesday?"}
    ).json()
    assert unknown["sources"] == []
    assert unknown["confidence"] == 0
    multi = client.post(
        "/api/chat",
        json={"question": "Find the semester 4 subjects and identify the practical courses."},
    ).json()
    assert multi["intent"] == "MULTI_STEP"
    assert multi["sources"]
    assert "execute_subtasks" in multi["graph_route"]


def test_chat_planner_creation_modification_and_calendar_are_real_graph_paths(client):
    created = client.post(
        "/api/chat",
        json={"question": "Create a 14-day plan for DBMS and OS. I have 3 hours per day."},
    ).json()
    assert created["intent"] == "STUDY_PLAN"
    assert "persist_plan" in created["graph_route"]
    assert created["tool_results"][0]["action"] == "created"

    modified = client.post(
        "/api/chat",
        json={
            "conversation_id": created["conversation_id"],
            "question": "I cannot study on Saturday.",
        },
    ).json()
    assert modified["intent"] == "STUDY_PLAN_MODIFICATION"
    assert "load_existing_plan" in modified["graph_route"]
    assert modified["tool_results"][0]["action"] == "updated"

    calendar = client.post(
        "/api/chat",
        json={"question": "Schedule DBMS revision tomorrow at 7 PM for 60 minutes."},
    ).json()
    assert calendar["intent"] == "CALENDAR_ACTION"
    assert "execute_calendar_tool" in calendar["graph_route"]
    assert calendar["tool_results"][0]["tool"] == "calendar_create_event"
