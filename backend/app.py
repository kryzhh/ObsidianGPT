from flask import Flask, request, Response
from flask_cors import CORS
import json

from rag_service import stream_answer, init

app = Flask(__name__)
CORS(app)

# sync vault on startup, then watch for changes in background
init()

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    query = data.get("message", "")

    def generate():
        for chunk in stream_answer(query):
            yield f"data: {json.dumps({'token': chunk})}\n\n"

    return Response(generate(), content_type="text/event-stream")

@app.route("/")
def index():
    return "Backend running"

if __name__ == "__main__":
    # Using reloader = false else it will spawn a second process which would start a second watcher
    # double index everything.
    app.run(port=5000, debug=True, use_reloader=False)