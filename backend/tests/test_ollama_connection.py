"""
Step 3 — Minimal test to verify Python can communicate with Ollama.

This script does NOT use any project services.
It directly calls Ollama's API to confirm:
  1. Ollama server is reachable
  2. qwen2.5:3b model is available
  3. We can send a message and get a response
"""

import ollama


def test_ollama_connection():
    print("=" * 60)
    print("TEST 1: Check if Ollama server is reachable")
    print("=" * 60)

    try:
        models = ollama.list()
        print("Ollama server is reachable!")
        print(f"Available models: {[m.model for m in models.models]}")
    except Exception as e:
        print(f"FAILED: Cannot connect to Ollama: {e}")
        print("Make sure Ollama is running (ollama serve)")
        return

    print()
    print("=" * 60)
    print("TEST 2: Send a simple message to qwen2.5:3b")
    print("=" * 60)

    try:
        response = ollama.chat(
            model="qwen2.5:3b",
            messages=[
                {
                    "role": "user",
                    "content": "What is Python? Answer in one sentence.",
                }
            ],
        )

        print(f"Model: {response.model}")
        print(f"Response: {response.message.content}")
        print(f"Done reason: {response.done_reason}")

        # Check if usage metadata is available
        print()
        print("Usage metadata:")
        print(f"  prompt_eval_count: {getattr(response, 'prompt_eval_count', 'N/A')}")
        print(f"  eval_count: {getattr(response, 'eval_count', 'N/A')}")
        print(f"  total_duration: {getattr(response, 'total_duration', 'N/A')}")

        print()
        print("SUCCESS: Ollama is working!")

    except Exception as e:
        print(f"FAILED: {e}")


if __name__ == "__main__":
    test_ollama_connection()
