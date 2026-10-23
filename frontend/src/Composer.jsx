import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowUpIcon, StopIcon } from "./icons";

const MAX_HEIGHT = 200;

export default function Composer({ onSend, onStop, isStreaming }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  // grow with content up to MAX_HEIGHT, then scroll
  useLayoutEffect(() => {
    const el = textareaRef.current;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  // hand focus back once an answer finishes so the next question can be typed straight away
  useEffect(() => {
    if (!isStreaming) textareaRef.current?.focus();
  }, [isStreaming]);

  const submit = () => {
    if (!value.trim() || isStreaming) return;
    onSend(value);
    setValue("");
  };

  return (
    <div className="composer-wrap">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <textarea
          ref={textareaRef}
          id="composer-input"
          aria-label="Message ObsidianGPT"
          rows={1}
          value={value}
          placeholder="Ask anything about your notes…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
        />
        {isStreaming ? (
          <button type="button" className="send-btn is-stop" onClick={onStop} aria-label="Stop generating">
            <StopIcon />
          </button>
        ) : (
          <button type="submit" className="send-btn" disabled={!value.trim()} aria-label="Send">
            <ArrowUpIcon />
          </button>
        )}
      </form>
      <p className="composer-hint">
        Enter to send · Shift + Enter for a new line · Quote a note's name to open it, e.g. "docker"
      </p>
    </div>
  );
}
