"""
Step 8 — Test the Streaming Chat Endpoint with Ollama.
"""

import sys
import os

backend_dir = os.path.join(os.path.dirname(__file__), "..")
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_streaming_endpoint():
    print("=" * 60)
    print("TEST: POST /api/v1/chat/stream (Streaming Chat)")
    print("=" * 60)

    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        json={
            "conversation_id": "test-step8-conv-1",
            "message": "Count from 1 to 5.",
        }
    ) as response:
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Streaming response chunks:")
            for chunk in response.iter_text():
                print(chunk, end="", flush=True)
            print("\n\nSUCCESS: Streaming endpoint is working!")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    test_streaming_endpoint()
