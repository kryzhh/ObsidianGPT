import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { useState } from "react";

/* 🔥 Separate component for code blocks */
function CodeBlock({ className, children }) {
  const [copied, setCopied] = useState(false);

  const codeText = Array.isArray(children)
    ? children.map((child) =>
        typeof child === "string"
          ? child
          : child?.props?.children || ""
      ).join("")
    : String(children || "");

  const handleCopy = () => {
    navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div style={{ marginTop: "10px" }}>
      <div style={{ position: "relative" }}>
        <button
          onClick={handleCopy}
          style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            fontSize: "11px",
            padding: "4px 8px",
            borderRadius: "6px",
            border: "1px solid rgba(255,255,255,0.1)",
            background: "rgba(0,0,0,0.6)",
            color: "#ddd",
            cursor: "pointer",
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>

        <pre
          style={{
            margin: 0,
            padding: "14px",
            borderRadius: "10px",
            background: "#1e1e1e",
            overflowX: "auto",
          }}
        >
          <code className={className}>{children}</code>
        </pre>
      </div>
    </div>
  );
}

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
            components={{
              code({ inline, className, children }) {
                if (inline) return <code>{children}</code>;
                return <CodeBlock className={className} children={children} />;
              },
            }}
          >
            {content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  );
}