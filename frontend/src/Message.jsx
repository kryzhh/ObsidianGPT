import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

export default function Message({ role, content, loading }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: role === "user" ? "flex-end" : "flex-start",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          background: role === "user" ? "#0b93f6" : "#444654",
          padding: "12px 14px",
          borderRadius: "12px",
          maxWidth: "75%",
          lineHeight: "1.5",
          fontSize: "14px",
        }}
      >
        {loading ? (
          <span className="typing">
            <span>.</span><span>.</span><span>.</span>
          </span>
        ) : role === "user" ? (
          content
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}