import argparse
import json
import os
import shutil
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from indexing.load import load_file
from indexing.chunk import chunk
from indexing.embed_and_store import embed_and_store

from retrieval.retrieval import retrieve

from generation.generation import generation

EMBEDDINGS = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# Load config
with open('.env.json', 'r') as file:
    ENV = json.load(file)

VAULT_DIR = ENV["VAULT"]
DB_PATH = Path("./chroma.db")
INDEX_STATE_PATH = Path("./index_state.json")


def parse_args():
    parser = argparse.ArgumentParser(description="Query your Obsidian vault with local RAG")
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force rebuilding the Chroma index from vault files"
    )
    return parser.parse_args()


def compute_vault_snapshot(vault_dir):
    # Capture relative path + mtime + size for markdown files.
    snapshot = {}
    vault = Path(vault_dir)

    for path in vault.rglob("*.md"):
        if not path.is_file():
            continue
        stat = path.stat()
        rel = path.relative_to(vault).as_posix()
        snapshot[rel] = {
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size
        }

    return snapshot


def load_index_state():
    if not INDEX_STATE_PATH.exists():
        return None
    with open(INDEX_STATE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_index_state(snapshot):
    state = {"vault_snapshot": snapshot}
    with open(INDEX_STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def has_vault_changed(vault_dir):
    state = load_index_state()
    if not state or "vault_snapshot" not in state:
        return True
    current_snapshot = compute_vault_snapshot(vault_dir)
    return current_snapshot != state["vault_snapshot"]


def build_index(vault_dir):
    print("Indexing vault...")
    all_chunks = []

    for root, _, files in os.walk(vault_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            docs = load_file(filepath)
            if docs:
                chunks = chunk(docs)
                all_chunks.extend(chunks)
                print(f"Indexed: {filepath}")

    if not all_chunks:
        raise RuntimeError("No markdown content found to index.")

    if DB_PATH.exists():
        if DB_PATH.is_dir():
            shutil.rmtree(DB_PATH)
        else:
            DB_PATH.unlink()

    vectorstore = embed_and_store(EMBEDDINGS, all_chunks)
    save_index_state(compute_vault_snapshot(vault_dir))
    print(f"Done. {len(all_chunks)} chunks stored.")
    return vectorstore


def load_existing_index():
    return Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=EMBEDDINGS
    )

# Validate vault folder exists
if not Path(VAULT_DIR).exists():
    print("Invalid vault folder")
    quit(0)

args = parse_args()

should_reindex = args.reindex
if not DB_PATH.exists():
    should_reindex = True
elif has_vault_changed(VAULT_DIR):
    print("Vault changed since last index. Re-indexing...")
    should_reindex = True

if should_reindex:
    vectorstore = build_index(VAULT_DIR)
else:
    print("Index up to date. Loading existing DB.")
    vectorstore = load_existing_index()

question = ""
while True:
    print('-------------------------------------------------------------------------')
    question = input("Enter your question (or 'quit'): ")
    if question.lower() == "quit":
        break

    retriever = retrieve(vectorstore, question)

    # DEBUG — see what chunks are actually being fetched
    # test_docs = retriever.invoke(question)
    # for i, doc in enumerate(test_docs):
    #     print(f"\n[Chunk {i+1}] source: {doc.metadata.get('source')}")
    #     print(doc.page_content[:100])
    # print("---")
    answer = generation(retriever, ENV["CHAT_MODEL"], question)
    print(answer)