import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from watchfiles import awatch

from indexing.load import load_file
from indexing.chunk import chunk

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
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep watching the vault and refresh the index when files change"
    )
    return parser.parse_args()


def compute_file_state(filepath):
    path = Path(filepath)
    stat = path.stat()
    return {
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def load_index_state():
    if not INDEX_STATE_PATH.exists():
        return None
    with open(INDEX_STATE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_index_state(files_state):
    state = {"files": files_state}
    with open(INDEX_STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def indexed_files_from_state(state):
    if not state:
        return {}

    if "files" in state:
        return state["files"]

    vault_snapshot = state.get("vault_snapshot", {})
    indexed_files = {}
    for rel_path, details in vault_snapshot.items():
        indexed_files[rel_path] = {
            "mtime_ns": details.get("mtime_ns"),
            "size": details.get("size"),
            "hash": None,
            "ids": [],
        }
    return indexed_files


def build_index(vault_dir):
    print("Indexing vault from scratch...")

    if DB_PATH.exists():
        if DB_PATH.is_dir():
            shutil.rmtree(DB_PATH)
        else:
            DB_PATH.unlink()

    vectorstore = load_existing_index()
    indexed_files = {}
    vault = Path(vault_dir)

    for root, _, files in os.walk(vault_dir):
        for filename in files:
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            rel_path = Path(filepath).relative_to(vault).as_posix()
            docs = load_file(filepath)
            if not docs:
                continue

            chunks = chunk(docs)
            if not chunks:
                continue

            file_hash = docs[0].metadata.get("content_hash")
            chunk_ids = [f"{rel_path}:{file_hash}:{index}" for index in range(len(chunks))]

            try:
                vectorstore.add_documents(chunks, ids=chunk_ids)
            except Exception as exc:
                print(f"Skipping embedding for {filepath}: {exc}")
                continue

            indexed_files[rel_path] = {
                "hash": file_hash,
                "mtime_ns": Path(filepath).stat().st_mtime_ns,
                "size": Path(filepath).stat().st_size,
                "ids": chunk_ids,
            }
            print(f"Indexed: {filepath}")

    if not indexed_files:
        raise RuntimeError("No markdown content found to index.")

    save_index_state(indexed_files)
    print(f"Done. {len(indexed_files)} files stored.")
    return vectorstore


def sync_index(vault_dir, state):
    print("Syncing vault changes...")
    previous_files = indexed_files_from_state(state)
    current_files = dict(previous_files)
    seen_files = set()
    vault = Path(vault_dir)
    vectorstore = load_existing_index()

    for root, _, files in os.walk(vault_dir):
        for filename in files:
            if not filename.endswith(".md"):
                continue

            filepath = os.path.join(root, filename)
            rel_path = Path(filepath).relative_to(vault).as_posix()
            seen_files.add(rel_path)

            docs = load_file(filepath)
            if not docs:
                continue

            current_state = compute_file_state(filepath)
            file_hash = docs[0].metadata.get("content_hash")
            previous_state = previous_files.get(rel_path, {})

            if previous_state.get("hash") == file_hash and previous_state.get("mtime_ns") == current_state["mtime_ns"] and previous_state.get("size") == current_state["size"]:
                previous_ids = previous_state.get("ids", [])
                if not previous_ids and rel_path in previous_files:
                    try:
                        previous_ids = vectorstore.get(where={"source": filepath}).get("ids", [])
                    except Exception as exc:
                        print(f"Warning: could not recover ids for {filepath}: {exc}")

                current_files[rel_path] = {
                    "hash": file_hash,
                    **current_state,
                    "ids": previous_ids,
                }
                continue

            chunks = chunk(docs)
            if not chunks:
                continue

            chunk_ids = [f"{rel_path}:{file_hash}:{index}" for index in range(len(chunks))]
            previous_ids = previous_state.get("ids", [])
            if not previous_ids and rel_path in previous_files:
                try:
                    previous_ids = vectorstore.get(where={"source": filepath}).get("ids", [])
                except Exception as exc:
                    print(f"Warning: could not recover ids for {filepath}: {exc}")

            try:
                vectorstore.add_documents(chunks, ids=chunk_ids)
            except Exception as exc:
                print(f"Skipping embedding for {filepath}: {exc}")
                continue

            if previous_ids:
                try:
                    vectorstore.delete(ids=previous_ids)
                except Exception as exc:
                    print(f"Warning: could not remove stale chunks for {filepath}: {exc}")

            current_files[rel_path] = {
                "hash": file_hash,
                **current_state,
                "ids": chunk_ids,
            }
            print(f"Indexed: {filepath}")

    removed_files = set(previous_files) - seen_files
    for rel_path in removed_files:
        removed_ids = previous_files.get(rel_path, {}).get("ids", [])
        source_path = str(vault / rel_path)
        if not removed_ids:
            try:
                removed_ids = vectorstore.get(where={"source": source_path}).get("ids", [])
            except Exception as exc:
                print(f"Warning: could not recover ids for deleted file {source_path}: {exc}")
        try:
            vectorstore.delete(ids=removed_ids)
        except Exception as exc:
            print(f"Warning: could not remove deleted file {source_path}: {exc}")
        current_files.pop(rel_path, None)

    save_index_state(current_files)
    print(f"Done. {len(current_files)} files tracked.")
    return vectorstore


def load_existing_index():
    return Chroma(
        persist_directory=str(DB_PATH),
        embedding_function=EMBEDDINGS
    )


async def watch_vault(vault_dir, vectorstore_box):
    print("Watching vault for changes...")
    async for _changes in awatch(vault_dir):
        print("Vault changed. Syncing index...")
        vectorstore_box["vectorstore"] = await asyncio.to_thread(sync_index, vault_dir, load_index_state())


async def chat_loop(vectorstore_box):
    while True:
        print('-------------------------------------------------------------------------')
        question = await asyncio.to_thread(input, "Enter your question (or 'quit'): ")
        if question.lower() == "quit":
            break

        retriever = retrieve(vectorstore_box["vectorstore"], question)

        # DEBUG — see what chunks are actually being fetched
        # test_docs = retriever.invoke(question)
        # for i, doc in enumerate(test_docs):
        #     print(f"\n[Chunk {i+1}] source: {doc.metadata.get('source')}")
        #     print(doc.page_content[:100])
        # print("---")
        answer = generation(retriever, ENV["CHAT_MODEL"], question)
        print(answer)


async def main():
    args = parse_args()

    # Validate vault folder exists
    if not Path(VAULT_DIR).exists():
        print("Invalid vault folder")
        return

    state = load_index_state()

    if args.reindex or not DB_PATH.exists() or not state:
        vectorstore = build_index(VAULT_DIR)
    else:
        vectorstore = sync_index(VAULT_DIR, state)

    vectorstore_box = {"vectorstore": vectorstore}
    watch_task = None

    if args.watch:
        watch_task = asyncio.create_task(watch_vault(VAULT_DIR, vectorstore_box))

    try:
        await chat_loop(vectorstore_box)
    finally:
        if watch_task:
            watch_task.cancel()
            try:
                await watch_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(main())