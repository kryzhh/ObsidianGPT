import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.retrieval import retrieve
from generation.generation import generation
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load config
with open(os.path.join(BASE_DIR, ".env.json"), "r") as file:
    ENV = json.load(file)

# Load embedding model
embedding = OllamaEmbeddings(
    model=ENV["EMBED_MODEL"],
    base_url="http://localhost:11434"
)

# Load vector DB
vectorstore = Chroma(
    persist_directory=os.path.join(BASE_DIR, "chroma.db"),
    embedding_function=embedding
)

model = ENV["CHAT_MODEL"]

def stream_answer(query: str):
    # IMPORTANT: retrieve depends on query
    retriever = retrieve(vectorstore, query)

    for chunk in generation(retriever, model, query, stream=True):
        yield chunk