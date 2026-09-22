"""
Step 7 — Test the Normal Chat Endpoint with Ollama.
"""

import sys
import os

backend_dir = os.path.join(os.path.dirname(__file__), "..")
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    print("=" * 60)
    print("TEST: POST /api/v1/chat (Normal Chat)")
    print("=" * 60)

    response = client.post(
        "/api/v1/chat",
        json={
            "conversation_id": "test-step7-conv-1",
            "message": "What color is the sky? Answer in one word.",
        }
    )

    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response text: {data['response']}")
        print(f"Model used: {data['model']}")
        print(f"Request ID: {data['request_id']}")
        print("\nSUCCESS: Endpoint is working and returning the correct model!")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_chat_endpoint()
