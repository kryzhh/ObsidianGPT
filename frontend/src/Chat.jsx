import { useState, useRef, useEffect } from "react";
import Message from "./Message";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: messages.length < 2 ? "auto" : "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input) return;
    await new Promise((r) => setTimeout(r, 300));

    const userMessage = { role: "user", content: input };
    const loadingMessage = { role: "assistant", content: "", loading: true };

    const newMessages = [...messages, userMessage, loadingMessage];
    setMessages(newMessages);
    setInput("");

    const res = await fetch("http://localhost:5000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: input }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let botMessage = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (let line of lines) {
        if (line.startsWith("data: ")) {
          const data = JSON.parse(line.replace("data: ", ""));
          botMessage += data.token;

          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: botMessage,
              loading: false,
            };
            return updated;
          });
        }
      }
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "800px",
            padding: "20px",
          }}
        >
          {messages.map((msg, i) => (
            <Message
              key={i}
              role={msg.role}
              content={msg.content}
              loading={msg.loading}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <div
        style={{
          borderTop: "none",
          padding: "15px",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "800px",
            display: "flex",
            gap: "10px",
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder="Message your assistant..."
            style={{
              flex: 1,
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid #666",
              background: "#40414f",
              color: "white",
              outline: "none",
            }}
          />
          <button
            onClick={sendMessage}
            style={{
              padding: "12px 16px",
              borderRadius: "8px",
              border: "none",
              background: "#0b93f6",
              color: "white",
              cursor: "pointer",
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}