from app.core.config import Settings


def enable_demo(monkeypatch):
    settings = Settings(
        demo_mode=True,
        llm_provider="local",
        embedding_provider="local",
    )
    monkeypatch.setattr("app.graph.workflow.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.demo.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.conversations.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.documents.get_settings", lambda: settings)
    monkeypatch.setattr("app.api.routes.plans.get_settings", lambda: settings)


def test_demo_mode_exposes_fixed_questions_answers_and_documents(client, monkeypatch):
    enable_demo(monkeypatch)
    status = client.get("/api/demo").json()
    assert status["enabled"] is True
    assert "What is the attendance requirement?" in status["questions"]

    known = client.post(
        "/api/chat", json={"question": "What is the attendance requirement?"}
    ).json()
    assert not known["answer"].startswith("Demo mode:")
    assert "85 percent" in known["answer"]
    assert known["sources"][0]["document_id"] == "demo-academic-regulations"
    assert "demo_response" in known["graph_route"]

    unknown = client.post(
        "/api/chat", json={"question": "What will the cafeteria serve next Tuesday?"}
    ).json()
    assert unknown["sources"] == []
    assert unknown["confidence"] == 0

    documents = client.get("/api/documents").json()
    assert len(documents) == 2
    assert all(document["status"] == "ready" for document in documents)
    assert all("demo" not in document["title"].lower() for document in documents)

    conversations = client.get("/api/conversations").json()
    assert len(conversations) == 3
    detail = client.get(f"/api/conversations/{conversations[0]['id']}").json()
    assert len(detail["messages"]) == 6
    assert all("Demo mode:" not in message["content"] for message in detail["messages"])


def test_demo_mode_seeds_a_predefined_plan(client, monkeypatch):
    enable_demo(monkeypatch)
    plans = client.get("/api/plans").json()
    assert len(plans) == 2
    exam_plan = next(plan for plan in plans if plan["title"] == "Examination preparation plan")
    assert {subject["name"] for subject in exam_plan["subjects"]} == {
        "DBMS",
        "Operating Systems",
    }
    assert exam_plan["sessions"]
