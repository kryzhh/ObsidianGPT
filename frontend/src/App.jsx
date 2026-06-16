import Chat from "./Chat";

export default function App() {
  return (
    <div
      style={{
        height: "100vh",
        background: "#343541",
        color: "white",
        display: "flex",
        flexDirection: "column",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      {/* 🔹 Header */}
      <div
        style={{
          padding: "12px 20px",
          borderBottom: "none",
          fontWeight: "600",
          fontSize: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span>ObsidianGPT</span>
        <span style={{ fontSize: "12px", color: "#aaa" }}>
          Local • RAG • Ollama
        </span>
      </div>

      {/* 🔹 Chat area */}
      <Chat />
    </div>
  );
}