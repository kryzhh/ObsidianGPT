import { useCallback, useEffect, useState } from "react";
import Chat from "./Chat";
import Composer from "./Composer";
import Sidebar from "./Sidebar";
import useChat, { API_URL } from "./useChat";
import { LogoIcon, MenuIcon, PlusIcon } from "./icons";

const SUGGESTIONS = [
  { title: "Revisit a memory", prompt: "What have I written about feeling lost?" },
  { title: "Find a poem", prompt: "Show me a poem I wrote" },
  { title: "Recap a topic", prompt: "Summarize my notes on Docker" },
  { title: "Study help", prompt: "What have I noted about dynamic programming?" },
];

const HEALTH_INTERVAL_MS = 15000;

function greeting() {
  const hour = new Date().getHours();
  if (hour < 5) return "Up late";
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

// Polls the backend root so the header can show whether questions will go through
function useBackendStatus() {
  const [online, setOnline] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const check = () =>
      fetch(`${API_URL}/`)
        .then((res) => !cancelled && setOnline(res.ok))
        .catch(() => !cancelled && setOnline(false));

    check();
    const timer = setInterval(check, HEALTH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return online;
}

function EmptyState({ onPick }) {
  return (
    <div className="empty">
      <div className="empty-logo">
        <LogoIcon size={30} />
      </div>
      <h1>{greeting()}.</h1>
      <p>What would you like to find in your vault?</p>

      <div className="suggestions">
        {SUGGESTIONS.map((s) => (
          <button key={s.title} type="button" className="suggestion" onClick={() => onPick(s.prompt)}>
            <span className="suggestion-title">{s.title}</span>
            <span className="suggestion-prompt">{s.prompt}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function App() {
  const { chats, chatId, messages, isStreaming, send, stop, retry, newChat, openChat, deleteChat } =
    useChat();
  const online = useBackendStatus();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  const statusLabel = online === null ? "Connecting" : online ? "Local · Ollama" : "Backend offline";
  const statusClass = online === null ? "" : online ? "is-online" : "is-offline";
  const title = chats.find((c) => c.id === chatId)?.title || "New chat";

  return (
    <div className="app">
      {/* moves focus in script: following "#composer-input" would overwrite the #<chat id> URL */}
      <a
        className="skip-link"
        href="#composer-input"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("composer-input")?.focus();
        }}
      >
        Skip to message box
      </a>

      <Sidebar
        chats={chats}
        activeId={chatId}
        open={sidebarOpen}
        onClose={closeSidebar}
        onNew={newChat}
        onOpen={openChat}
        onDelete={deleteChat}
      />

      <div className="content">
        <header className="topbar">
          <div className="topbar-title">
            <button
              type="button"
              className="icon-btn menu-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open chats"
            >
              <MenuIcon />
            </button>
            <span title={title}>{title}</span>
          </div>

          <div className="topbar-actions">
            <span className={`status ${statusClass}`}>
              <span className="status-dot" />
              {statusLabel}
            </span>
            <button
              type="button"
              className="icon-btn menu-btn"
              onClick={newChat}
              aria-label="New chat"
            >
              <PlusIcon />
            </button>
          </div>
        </header>

        <main className="main">
          {messages.length === 0 ? (
            <EmptyState onPick={send} />
          ) : (
            <Chat messages={messages} onRetry={retry} />
          )}
          <Composer onSend={send} onStop={stop} isStreaming={isStreaming} />
        </main>
      </div>
    </div>
  );
}
