# Turns stored chat messages into a compact transcript for prompts.
#
# Follow-ups almost always refer to the latest answer, so that one is kept nearly whole while
# older answers are cut to their opening (where the gist usually is). Messages are added newest
# first until the budget is used up, then the rest are dropped. At ~4 chars per token the
# default budget is ~1000 tokens, leaving room in NUM_CTX for a whole note plus the answer.

HISTORY_CHAR_BUDGET = 4000
LATEST_REPLY_CHARS = 2000
OLDER_REPLY_CHARS = 500
QUESTION_CHARS = 500


def _shorten(text, limit):
    # collapse newlines/indentation, which cost tokens without helping the model follow along
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + " …"


def format_history(messages, char_budget=HISTORY_CHAR_BUDGET):
    lines = []
    used = 0
    seen_reply = False

    for msg in reversed(messages):
        if msg["role"] == "assistant":
            text = _shorten(msg["content"], OLDER_REPLY_CHARS if seen_reply else LATEST_REPLY_CHARS)
            seen_reply = True
            # naming the notes lets "that letter" be resolved to an actual note title
            label = "Assistant"
            if msg.get("sources"):
                label += f" (from notes: {', '.join(msg['sources'])})"
        else:
            text = _shorten(msg["content"], QUESTION_CHARS)
            label = "User"

        line = f"{label}: {text}"
        if lines and used + len(line) > char_budget:
            break
        lines.append(line)
        used += len(line)

    return "\n".join(reversed(lines))
