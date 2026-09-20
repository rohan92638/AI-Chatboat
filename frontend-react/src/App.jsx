import { useState, useCallback, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import { streamMessage } from './api/chat';
import './index.css';

/**
 * Root App component.
 * Manages conversations, messages, and streaming state.
 */
export default function App() {
  // ── State ──
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem('chatbot-conversations');
    if (saved) {
      try { return JSON.parse(saved); } catch { /* ignore */ }
    }
    const id = uuidv4();
    return [{ id, title: 'New Chat', messages: [] }];
  });

  const [activeConvId, setActiveConvId] = useState(() => {
    const saved = localStorage.getItem('chatbot-active-id');
    if (saved && conversations.some((c) => c.id === saved)) return saved;
    return conversations[0]?.id;
  });

  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const abortRef = useRef(null);

  // ── Persistence ──
  const persist = (convs, activeId) => {
    localStorage.setItem('chatbot-conversations', JSON.stringify(convs));
    if (activeId) localStorage.setItem('chatbot-active-id', activeId);
  };

  // ── Get active conversation ──
  const activeConv = conversations.find((c) => c.id === activeConvId);
  const activeMessages = activeConv?.messages || [];

  // ── Update messages for a conversation ──
  const updateMessages = useCallback((convId, updater) => {
    setConversations((prev) => {
      const next = prev.map((c) => {
        if (c.id !== convId) return c;
        const newMessages = typeof updater === 'function' ? updater(c.messages) : updater;
        // Update title from first user message if still "New Chat"
        let title = c.title;
        if (title === 'New Chat') {
          const firstUser = newMessages.find((m) => m.role === 'user');
          if (firstUser) {
            title = firstUser.content.slice(0, 40) + (firstUser.content.length > 40 ? '...' : '');
          }
        }
        return { ...c, messages: newMessages, title };
      });
      persist(next, convId);
      return next;
    });
  }, []);

  // ── Send message (streaming) ──
  const handleSend = useCallback((text) => {
    if (!text.trim() || isLoading) return;

    const convId = activeConvId;

    // Add user message
    updateMessages(convId, (msgs) => [...msgs, { role: 'user', content: text }]);

    setIsLoading(true);
    setIsStreaming(false);

    // Add empty assistant message placeholder
    setTimeout(() => {
      updateMessages(convId, (msgs) => [...msgs, { role: 'assistant', content: '' }]);
    }, 0);

    const controller = streamMessage(convId, text, {
      onChunk: (_chunk, fullText) => {
        setIsStreaming(true);
        // Update the last assistant message with accumulated text
        updateMessages(convId, (msgs) => {
          const newMsgs = [...msgs];
          const lastIdx = newMsgs.length - 1;
          if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant') {
            newMsgs[lastIdx] = { ...newMsgs[lastIdx], content: fullText };
          }
          return newMsgs;
        });
      },
      onDone: (_fullText) => {
        setIsLoading(false);
        setIsStreaming(false);
        abortRef.current = null;
      },
      onError: (err) => {
        setIsLoading(false);
        setIsStreaming(false);
        abortRef.current = null;
        // Replace the empty assistant message with an error
        updateMessages(convId, (msgs) => {
          const newMsgs = [...msgs];
          const lastIdx = newMsgs.length - 1;
          if (lastIdx >= 0 && newMsgs[lastIdx].role === 'assistant' && !newMsgs[lastIdx].content) {
            newMsgs[lastIdx] = { role: 'error', content: err.message || 'Something went wrong. Please try again.' };
          } else {
            newMsgs.push({ role: 'error', content: err.message || 'Something went wrong. Please try again.' });
          }
          return newMsgs;
        });
      },
    });

    abortRef.current = controller;
  }, [activeConvId, isLoading, updateMessages]);

  // ── Conversation management ──
  const handleNewChat = useCallback(() => {
    // Cancel any in-flight stream
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setIsLoading(false);
      setIsStreaming(false);
    }

    const id = uuidv4();
    const newConv = { id, title: 'New Chat', messages: [] };
    setConversations((prev) => {
      const next = [newConv, ...prev];
      persist(next, id);
      return next;
    });
    setActiveConvId(id);
    setSidebarOpen(false);
  }, []);

  const handleSelectConversation = useCallback((id) => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setIsLoading(false);
      setIsStreaming(false);
    }
    setActiveConvId(id);
    localStorage.setItem('chatbot-active-id', id);
    setSidebarOpen(false);
  }, []);

  const handleDeleteConversation = useCallback((id) => {
    setConversations((prev) => {
      const next = prev.filter((c) => c.id !== id);
      // If deleting the active conversation, switch to the first remaining one or create new
      if (id === activeConvId) {
        if (next.length > 0) {
          setActiveConvId(next[0].id);
          persist(next, next[0].id);
        } else {
          const newId = uuidv4();
          const newConv = { id: newId, title: 'New Chat', messages: [] };
          next.push(newConv);
          setActiveConvId(newId);
          persist(next, newId);
        }
      } else {
        persist(next, activeConvId);
      }
      return next;
    });
  }, [activeConvId]);

  const handleSuggestionClick = useCallback((text) => {
    handleSend(text);
  }, [handleSend]);

  return (
    <div className="app-layout">
      <Sidebar
        conversations={conversations}
        activeId={activeConvId}
        onSelect={handleSelectConversation}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
      />
      <ChatArea
        messages={activeMessages}
        isLoading={isLoading}
        isStreaming={isStreaming}
        onSend={handleSend}
        onSuggestionClick={handleSuggestionClick}
      />
    </div>
  );
}
