import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './MessageBubble.css';

export default function MessageBubble({ role, content, isStreaming }) {
  const isUser = role === 'user';
  const isError = role === 'error';

  return (
    <div className={`message-bubble ${role}`} id={`msg-${Date.now()}`}>
      {/* Avatar */}
      <div className="message-avatar">
        {isUser ? 'U' : isError ? '!' : 'AI'}
      </div>

      {/* Content */}
      <div className="message-content">
        <div className="message-role">
          {isUser ? 'You' : isError ? 'Error' : 'AI Assistant'}
        </div>
        <div className="message-text">
          {isUser || isError ? (
            content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          )}
          {isStreaming && <span className="streaming-cursor" />}
        </div>
      </div>
    </div>
  );
}
