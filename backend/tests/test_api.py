from datetime import date, timedelta


def test_calculator_chat_and_conversation_persistence(client):
    response = client.post("/api/chat", json={"question": "What is 18% of 750?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The result is 135."
    conversation = client.get(f"/api/conversations/{body['conversation_id']}")
    assert conversation.status_code == 200
    assert len(conversation.json()["messages"]) == 2


def test_create_and_modify_plan(client):
    response = client.post(
        "/api/plans",
        json={
            "subjects": [{"name": "DBMS", "topics": ["SQL", "Transactions"], "difficulty": 4}],
            "exam_date": (date.today() + timedelta(days=12)).isoformat(),
            "available_hours_per_day": 2,
        },
    )
    assert response.status_code == 201
    plan = response.json()
    modified = client.patch(
        f"/api/plans/{plan['id']}", json={"instruction": "I cannot study on Saturday"}
    )
    assert modified.status_code == 200
    assert modified.json()["version"] == 2
