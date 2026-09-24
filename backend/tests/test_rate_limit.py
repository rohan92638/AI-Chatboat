from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rate_limit_on_chat():
    responses = []

    for _ in range(11):
        response = client.post(
            "/api/v1/chat",
            json={
                "message": "Hello",
                "conversation_id": "test-123",
            },
        )
        responses.append(response.status_code)

    assert 429 in responses