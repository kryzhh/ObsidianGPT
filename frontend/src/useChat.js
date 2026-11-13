import { useCallback, useEffect, useRef, useState } from "react";

export const API_URL = "http://localhost:5000";

const ACTIVE_CHAT_KEY = "obsidiangpt.activeChat";

function readActiveChat() {
  try {
    return localStorage.getItem(ACTIVE_CHAT_KEY);
  } catch {
    return null;
  }
}

function writeActiveChat(id) {
  try {
    if (id) localStorage.setItem(ACTIVE_CHAT_KEY, id);
    else localStorage.removeItem(ACTIVE_CHAT_KEY);
  } catch {
    // storage unavailable; the chat just won't reopen after a reload
  }
}

// The open chat lives in the URL hash (#<chat id>) so chats can be bookmarked and
// browser Back/Forward moves between them
function chatIdFromUrl() {
  return decodeURIComponent(window.location.hash.slice(1)) || null;
}

function writeUrl(id, push) {
  if (chatIdFromUrl() === id) return;
  const url = id ? `#${encodeURIComponent(id)}` : window.location.pathname + window.location.search;
  window.history[push ? "pushState" : "replaceState"](null, "", url);
}

async function fetchChat(id) {
  const res = await fetch(`${API_URL}/chats/${id}`);
  if (!res.ok) throw new Error("Chat not found");
  return res.json();
}

// Chats are stored by the backend; this hook holds the open one and the sidebar list.
// Assistant message status: "thinking" (waiting for first token) → "streaming" → "done",
// or "stopped" / "error"
export default function useChat() {
  const [chats, setChats] = useState([]);
  const [chatId, setChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(null);
  const chatIdRef = useRef(null);
  const nextId = useRef(0);
  const messagesRef = useRef(messages);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // `push` adds a history entry (user navigation); otherwise the current entry is replaced
  const selectChat = (id, push = false) => {
    chatIdRef.current = id;
    setChatId(id);
    writeActiveChat(id);
    writeUrl(id, push);
  };

  const refreshChats = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/chats`);
      if (res.ok) setChats(await res.json());
    } catch {
      // backend offline; the header status already says so
    }
  }, []);

  const resetChat = useCallback((push) => {
    abortRef.current?.abort();
    selectChat(null, push);
    setMessages([]);
  }, []);

  const newChat = useCallback(() => resetChat(true), [resetChat]);

  const showChat = useCallback((chat, push = false) => {
    selectChat(chat.id, push);
    setMessages(chat.messages.map((msg) => ({ ...msg, id: nextId.current++, status: "done" })));
  }, []);

  const loadChat = useCallback(
    async (id, push) => {
      abortRef.current?.abort();
      try {
        showChat(await fetchChat(id), push);
      } catch {
        resetChat(false);
      }
    },
    [showChat, resetChat]
  );

  const openChat = useCallback((id) => loadChat(id, true), [loadChat]);

  // load the sidebar and reopen the chat from the URL, else the last one used
  useEffect(() => {
    fetch(`${API_URL}/chats`)
      .then((res) => (res.ok ? res.json() : []))
      .then(setChats)
      .catch(() => {});

    const initial = chatIdFromUrl() || readActiveChat();
    if (initial) {
      fetchChat(initial)
        .then((chat) => showChat(chat))
        .catch(() => {
          writeActiveChat(null);
          writeUrl(null, false);
        });
    }
  }, [showChat]);

  // browser Back/Forward between chats
  useEffect(() => {
    const onPopState = () => {
      const id = chatIdFromUrl();
      if (id === chatIdRef.current) return;
      if (id) loadChat(id, false);
      else resetChat(false);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [loadChat, resetChat]);

  const send = useCallback(
    async (text) => {
      const question = text.trim();
      if (!question || abortRef.current) return;

      const userId = nextId.current++;
      const botId = nextId.current++;
      setMessages((prev) => [
        ...prev,
        { id: userId, role: "user", content: question },
        { id: botId, role: "assistant", content: "", status: "thinking", question },
      ]);

      const update = (patch) =>
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botId ? { ...msg, ...(typeof patch === "function" ? patch(msg) : patch) } : msg
          )
        );

      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      try {
        const res = await fetch(`${API_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: question, chat_id: chatIdRef.current }),
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`The backend returned an error (HTTP ${res.status}).`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // a network chunk can end mid-event, so only parse complete "data: ...\n\n" events
          buffer += decoder.decode(value, { stream: true });
          const events = buffer.split("\n\n");
          buffer = events.pop();

          for (const event of events) {
            if (!event.startsWith("data: ")) continue;
            const data = JSON.parse(event.slice(6));

            if (data.chat) {
              selectChat(data.chat.id);
            } else if (data.sources) {
              update({ sources: data.sources });
            } else if (data.token) {
              update((msg) => ({ content: msg.content + data.token, status: "streaming" }));
            }
          }
        }
        update({ status: "done" });
      } catch (err) {
        if (err.name === "AbortError") {
          update({ status: "stopped" });
        } else {
          update({
            status: "error",
            error:
              err instanceof TypeError
                ? "Couldn't reach the backend. Make sure `python app.py` is running on port 5000."
                : err.message,
          });
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setIsStreaming(false);
        refreshChats();
      }
    },
    [refreshChats]
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const deleteChat = useCallback(
    async (id) => {
      try {
        await fetch(`${API_URL}/chats/${id}`, { method: "DELETE" });
      } catch {
        return;
      }
      // replace rather than push, so Back doesn't lead to the deleted chat
      if (id === chatIdRef.current) resetChat(false);
      refreshChats();
    },
    [resetChat, refreshChats]
  );

  // Drop the failed exchange and ask the same question again. The backend already discarded
  // the failed question, so it isn't duplicated in the chat's history. Reads messages through
  // a ref so this callback stays stable and memoized messages don't re-render on every token.
  const retry = useCallback(
    (botId) => {
      const failed = messagesRef.current.find((msg) => msg.id === botId);
      if (!failed) return;
      setMessages((prev) => prev.filter((msg) => msg.id !== botId && msg.id !== botId - 1));
      send(failed.question);
    },
    [send]
  );

  return {
    chats,
    chatId,
    messages,
    isStreaming,
    send,
    stop,
    retry,
    newChat,
    openChat,
    deleteChat,
  };
}
