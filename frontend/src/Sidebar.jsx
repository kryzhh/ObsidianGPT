import { useEffect, useState } from "react";
import { LogoIcon, PlusIcon, TrashIcon } from "./icons";

const DAY_MS = 24 * 60 * 60 * 1000;

// Bucket chats by last activity: Today / Yesterday / Previous 7 days / Older
function groupChats(chats) {
  const startOfToday = new Date().setHours(0, 0, 0, 0);
  const groups = [
    { label: "Today", from: startOfToday, items: [] },
    { label: "Yesterday", from: startOfToday - DAY_MS, items: [] },
    { label: "Previous 7 days", from: startOfToday - 7 * DAY_MS, items: [] },
    { label: "Older", from: -Infinity, items: [] },
  ];
  for (const chat of chats) {
    const updated = chat.updated_at * 1000;
    groups.find((g) => updated >= g.from).items.push(chat);
  }
  return groups.filter((g) => g.items.length > 0);
}

function ChatItem({ chat, active, onOpen, onDelete }) {
  // first click arms delete, second confirms; disarms on its own after a moment
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (!confirming) return;
    const timer = setTimeout(() => setConfirming(false), 3000);
    return () => clearTimeout(timer);
  }, [confirming]);

  return (
    <li className={`chat-item ${active ? "is-active" : ""}`}>
      <button
        type="button"
        className="chat-item-open"
        onClick={() => onOpen(chat.id)}
        title={chat.title}
        aria-current={active ? "page" : undefined}
      >
        {chat.title}
      </button>
      <button
        type="button"
        className={`chat-item-delete ${confirming ? "is-confirming" : ""}`}
        onClick={() => (confirming ? onDelete(chat.id) : setConfirming(true))}
        aria-label={confirming ? "Confirm delete" : "Delete chat"}
      >
        {confirming ? "Delete?" : <TrashIcon />}
      </button>
    </li>
  );
}

export default function Sidebar({ chats, activeId, open, onClose, onNew, onOpen, onDelete }) {
  // on narrow screens the sidebar is an overlay, so close it after any navigation
  const handle = (fn) => (...args) => {
    fn(...args);
    onClose();
  };

  // Esc dismisses the overlay sidebar
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      <aside className={`sidebar ${open ? "is-open" : ""}`} aria-label="Chats">
        <div className="sidebar-head">
          <div className="brand">
            <LogoIcon size={20} />
            <span>ObsidianGPT</span>
          </div>
        </div>

        <button type="button" className="new-chat" onClick={handle(onNew)}>
          <PlusIcon />
          <span>New chat</span>
        </button>

        <nav className="chat-list">
          {chats.length === 0 && <p className="chat-list-empty">Your conversations will show up here.</p>}

          {groupChats(chats).map((group) => (
            <section key={group.label}>
              <h2>{group.label}</h2>
              <ul>
                {group.items.map((chat) => (
                  <ChatItem
                    key={chat.id}
                    chat={chat}
                    active={chat.id === activeId}
                    onOpen={handle(onOpen)}
                    onDelete={onDelete}
                  />
                ))}
              </ul>
            </section>
          ))}
        </nav>
      </aside>

      {open && <div className="sidebar-backdrop" onClick={onClose} />}
    </>
  );
}
