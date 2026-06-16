export default function Message({ role, content, loading }) {
  return (
    <div
      style={{
        textAlign: role === "user" ? "right" : "left",
        margin: "10px 0",
      }}
    >
      <span
        style={{
          background: role === "user" ? "#0b93f6" : "#444654",
          padding: "10px",
          borderRadius: "10px",
          display: "inline-block",
          maxWidth: "70%",
        }}
      >
        {loading ? (
          <span className="typing">
            <span>.</span><span>.</span><span>.</span>
          </span>
        ) : (
          content
        )}
      </span>
    </div>
  );
}