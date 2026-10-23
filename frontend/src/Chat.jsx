import { useEffect, useRef, useState } from "react";
import Message from "./Message";
import { ArrowDownIcon } from "./icons";

// px from the bottom within which the view keeps following new tokens
const STICK_THRESHOLD = 80;

export default function Chat({ messages, onRetry }) {
  const scrollRef = useRef(null);
  const stickRef = useRef(true);
  const userCountRef = useRef(0);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = (behavior = "auto") => {
    const el = scrollRef.current;
    el.scrollTo({ top: el.scrollHeight, behavior });
  };

  // Follow streaming output only while the reader is at the bottom; sending a new
  // question always snaps back down
  useEffect(() => {
    const userCount = messages.filter((msg) => msg.role === "user").length;
    if (userCount > userCountRef.current) stickRef.current = true;
    userCountRef.current = userCount;

    if (stickRef.current) scrollToBottom();
  }, [messages]);

  const handleScroll = () => {
    const el = scrollRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_THRESHOLD;
    stickRef.current = atBottom;
    setShowJump(!atBottom);
  };

  // One polite status for screen readers, announced on state changes rather than per token.
  // Errors aren't repeated here since the error block itself is role="alert".
  const last = messages[messages.length - 1];
  const announcement =
    last?.role !== "assistant"
      ? ""
      : { thinking: "Searching your notes", done: "Answer ready", stopped: "Answer stopped" }[
          last.status
        ] || "";

  return (
    <div className="chat-scroll" ref={scrollRef} onScroll={handleScroll}>
      <p className="sr-only" role="status">
        {announcement}
      </p>
      <div className="chat-column">
        {messages.map((msg) => (
          <Message key={msg.id} message={msg} onRetry={onRetry} />
        ))}
      </div>

      {showJump && (
        <button
          type="button"
          className="jump-btn"
          onClick={() =>
            scrollToBottom(
              window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
            )
          }
          aria-label="Scroll to latest"
        >
          <ArrowDownIcon />
        </button>
      )}
    </div>
  );
}
