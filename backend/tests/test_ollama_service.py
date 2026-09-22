"""
Step 4 — Test OllamaService.generate_response() directly.

This uses our actual OllamaService class (not the raw ollama client).
It verifies the service returns the correct format:
  {"response": "...", "model": "...", "usage_metadata": ...}
"""

import sys
import os

# Change working directory to backend/ so config.py can find app/.env
backend_dir = os.path.join(os.path.dirname(__file__), "..")
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.services.ollama_service import OllamaService


def test_ollama_service():
    service = OllamaService()

    print("=" * 60)
    print("TEST: OllamaService.generate_response()")
    print("=" * 60)

    result = service.generate_response(
        user_message="What is FastAPI? Answer in one sentence.",
        request_id="test-step4-001",
        history=[],
    )

    print(f"Response: {result['response']}")
    print(f"Model: {result['model']}")
    print(f"Usage metadata type: {type(result['usage_metadata'])}")

    usage = result["usage_metadata"]
    print(f"  prompt_eval_count: {getattr(usage, 'prompt_eval_count', 'N/A')}")
    print(f"  eval_count: {getattr(usage, 'eval_count', 'N/A')}")

    print()
    print("=" * 60)
    print("TEST: OllamaService with conversation history")
    print("=" * 60)

    history = [
        {"role": "user", "content": "My name is Rohan."},
        {"role": "assistant", "content": "Hello Rohan! How can I help you?"},
    ]

    result2 = service.generate_response(
        user_message="What is my name?",
        request_id="test-step4-002",
        history=history,
    )

    print(f"Response: {result2['response']}")
    print(f"Model: {result2['model']}")

    print()
    print("SUCCESS: OllamaService is working!")


if __name__ == "__main__":
    test_ollama_service()
