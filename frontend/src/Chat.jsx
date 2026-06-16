import { useState } from "react";
import Message from "./Message";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

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
      <div style={{ flex: 1, overflowY: "auto", padding: "20px" }}>
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} content={msg.content} />
        ))}
      </div>

      <div style={{ padding: "10px", borderTop: "1px solid #555" }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={{ width: "80%", padding: "10px" }}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}