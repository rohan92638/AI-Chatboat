import { useEffect, useState } from 'react';
import { checkHealth } from '../api/chat';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onDelete,
  isOpen,
  onToggle,
}) {
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    let mounted = true;
    const check = async () => {
      const ok = await checkHealth();
      if (mounted) setIsHealthy(ok);
    };
    check();
    const interval = setInterval(check, 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      {/* Mobile toggle button */}
      <button className="sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={onToggle}
      />

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        {/* Header */}
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={onNewChat} id="new-chat-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Conversation List */}
        <div className="sidebar-conversations">
          {conversations.length > 0 && (
            <div className="sidebar-section-label">Conversations</div>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              className={`conversation-item ${conv.id === activeId ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
              title={conv.title}
              id={`conv-${conv.id.slice(0, 8)}`}
            >
              <svg className="conversation-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span className="conversation-title">{conv.title}</span>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
                aria-label="Delete conversation"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </button>
          ))}
        </div>

        {/* Footer with health indicator */}
        <div className="sidebar-footer">
          <div className={`health-indicator ${isHealthy ? 'connected' : 'disconnected'}`} />
          <span className="health-text">
            {isHealthy ? 'Backend connected' : 'Backend offline'}
          </span>
        </div>
      </aside>
    </>
  );
}
