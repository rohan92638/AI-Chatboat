import { useRef, useEffect } from 'react';
import './ChatInput.css';

export default function ChatInput({ onSend, disabled }) {
  const textareaRef = useRef(null);

  // Auto-resize textarea as content grows
  const adjustHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = () => {
    const text = textareaRef.current?.value.trim();
    if (!text || disabled) return;
    onSend(text);
    textareaRef.current.value = '';
    textareaRef.current.style.height = 'auto';
    textareaRef.current.focus();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-input-area">
      <div className="chat-input-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input-textarea"
          placeholder="Type your message..."
          rows={1}
          onInput={adjustHeight}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          id="chat-input"
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={disabled}
          aria-label="Send message"
          id="send-btn"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
      <div className="chat-input-hint">
        Press <strong>Enter</strong> to send · <strong>Shift + Enter</strong> for new line
      </div>
    </div>
  );
}
