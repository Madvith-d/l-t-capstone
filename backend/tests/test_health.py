def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_question_is_rejected(client):
    response = client.post("/api/chat", json={"question": ""})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
