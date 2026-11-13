from flask import Flask, request, Response
from flask_cors import CORS
import json

import chat_store
from rag_service import stream_answer, init

# Only the most recent messages can fit the prompt's history budget, so don't load more
HISTORY_LOAD_LIMIT = 20

app = Flask(__name__)
CORS(app)

chat_store.init_db()

# sync vault on startup, then watch for changes in background
init()


def _sse(payload):
    return f"data: {json.dumps(payload)}\n\n"


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    query = data.get("message", "").strip()
    chat_id = data.get("chat_id")

    if not query:
        return {"error": "Message is empty"}, 400

    if chat_id:
        chat_meta = chat_store.get_chat(chat_id)
        if not chat_meta:
            return {"error": "Chat not found"}, 404
    else:
        chat_meta = chat_store.create_chat(query)

    # history is read before the new question is stored, so it holds earlier turns only
    history = chat_store.get_messages(chat_meta["id"], limit=HISTORY_LOAD_LIMIT)
    user_message_id = chat_store.add_message(chat_meta["id"], "user", query)

    def generate():
        answer = ""
        sources = []
        try:
            yield _sse({"chat": chat_meta})
            for event in stream_answer(query, history):
                if "sources" in event:
                    sources = event["sources"]
                else:
                    answer += event["token"]
                yield _sse(event)
        finally:
            # also runs when the client disconnects (Stop button): keep whatever was generated.
            # If nothing was, drop the question too so a failed turn doesn't linger in history.
            if answer:
                chat_store.add_message(chat_meta["id"], "assistant", answer, sources)
            else:
                chat_store.delete_message(user_message_id)

    return Response(generate(), content_type="text/event-stream")


@app.route("/chats", methods=["GET"])
def list_chats():
    return chat_store.list_chats()


@app.route("/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    chat_meta = chat_store.get_chat(chat_id)
    if not chat_meta:
        return {"error": "Chat not found"}, 404
    return {**chat_meta, "messages": chat_store.get_messages(chat_id)}


@app.route("/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    if not chat_store.delete_chat(chat_id):
        return {"error": "Chat not found"}, 404
    return {"ok": True}


@app.route("/")
def index():
    return "Backend running"

if __name__ == "__main__":
    # Using reloader = false else it will spawn a second process which would start a second watcher
    # double index everything.
    app.run(port=5000, debug=True, use_reloader=False)
