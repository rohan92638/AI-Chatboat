import './TypingIndicator.css';

export default function TypingIndicator() {
  return (
    <div className="typing-indicator-wrapper">
      <div className="typing-avatar">AI</div>
      <div className="typing-indicator-content">
        <div className="typing-label">AI Assistant</div>
        <div className="typing-dots">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  );
}
