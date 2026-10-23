import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { memo, useEffect, useState } from "react";
import { CheckIcon, CopyIcon, LogoIcon, NoteIcon, RetryIcon } from "./icons";

// Flatten rendered children (including highlight.js spans) back to plain text for copying
function textOf(node) {
  if (node == null || typeof node === "boolean") return "";
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  return textOf(node.props?.children);
}

function CopyButton({ text, label }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard unavailable (e.g. non-secure context); nothing useful to do
    }
  };

  return (
    <button type="button" className="icon-btn" onClick={handleCopy} aria-label="Copy">
      {copied ? <CheckIcon /> : <CopyIcon />}
      {label && <span>{copied ? "Copied" : "Copy"}</span>}
    </button>
  );
}

// react-markdown no longer tells `code` whether it's inline, so fenced blocks are styled via `pre`
function CodeBlock({ children }) {
  const code = Array.isArray(children) ? children[0] : children;
  const language = /language-(\S+)/.exec(code?.props?.className || "")?.[1];

  return (
    <div className="code-block">
      <div className="code-header">
        <span>{language || "code"}</span>
        <CopyButton text={textOf(code)} label />
      </div>
      <pre>{children}</pre>
    </div>
  );
}

const markdownComponents = {
  pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  ),
};

// The first token can take a minute when the model runs on CPU, so after a few seconds say why
const SLOW_AFTER_S = 8;

function Thinking() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const label =
    seconds < SLOW_AFTER_S
      ? "Searching your notes"
      : `Still working (${seconds}s). Local models can take a minute`;

  return (
    <div className="thinking">
      <span className="dots">
        <span />
        <span />
        <span />
      </span>
      <span className="shimmer">{label}</span>
    </div>
  );
}

// memo: while one answer streams, the rest of the conversation doesn't re-parse its markdown
export default memo(function Message({ message, onRetry }) {
  const { role, content, status } = message;

  if (role === "user") {
    return (
      <div className="msg msg-user">
        <div className="bubble">{content}</div>
      </div>
    );
  }

  return (
    <div className="msg msg-assistant">
      <div className="avatar">
        <LogoIcon size={16} />
      </div>

      <div className="msg-body">
        {status === "thinking" && <Thinking />}

        {content && (
          <div className={`markdown ${status === "streaming" ? "is-streaming" : ""}`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {status === "stopped" && <p className="note">Stopped.</p>}

        {status === "error" && (
          <div className="error" role="alert">
            <p>{message.error}</p>
            <button type="button" className="icon-btn" onClick={() => onRetry(message.id)}>
              <RetryIcon />
              <span>Retry</span>
            </button>
          </div>
        )}

        {message.sources?.length > 0 && content && (
          <div className="sources" aria-label="Notes used for this answer">
            {message.sources.map((name) => (
              <span key={name} className="source-chip" title={name}>
                <NoteIcon />
                {name}
              </span>
            ))}
          </div>
        )}

        {(status === "done" || status === "stopped") && content && (
          <div className="msg-actions">
            <CopyButton text={content} />
          </div>
        )}
      </div>
    </div>
  );
});
