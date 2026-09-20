/* ========================================================
   API Service Layer
   Handles all communication with the FastAPI backend.
   ======================================================== */

const API_BASE = '/api/v1';

/**
 * Send a normal (non-streaming) chat message.
 * Returns the full JSON response.
 */
export async function sendMessage(conversationId, message) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversation_id: conversationId,
      message: message,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error.detail || `Request failed with status ${response.status}`
    );
  }

  return response.json();
}


/**
 * Send a streaming chat message.
 * Calls `onChunk(text)` for every chunk received.
 * Calls `onDone(fullText)` when the stream completes.
 * Calls `onError(error)` if something goes wrong.
 * Returns an abort controller so the caller can cancel.
 */
export function streamMessage(conversationId, message, { onChunk, onDone, onError }) {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: message,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
          error.detail || `Request failed with status ${response.status}`
        );
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;
        onChunk(chunk, fullText);
      }

      onDone(fullText);
    } catch (err) {
      if (err.name === 'AbortError') return;
      onError(err);
    }
  })();

  return controller;
}


/**
 * Check backend health.
 */
export async function checkHealth() {
  try {
    const response = await fetch('/health', { signal: AbortSignal.timeout(5000) });
    if (!response.ok) return false;
    const data = await response.json();
    return data.status === 'ok';
  } catch {
    return false;
  }
}
