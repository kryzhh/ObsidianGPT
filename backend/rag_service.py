import sys
import os
import json
from pathlib import Path

# Since Flask is async, we need a seperate thread to watcht the vault files
import threading

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.retrieval import retrieve, find_target_notes, load_whole_files
from retrieval.rag_fusion import rag_fusion_retrieve
from retrieval.multi_query import generate_queries
from generation.generation import generation
from generation.history import format_history
from indexing.load import load_file
from indexing.chunk import chunk
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from watchfiles import watch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load config
with open(os.path.join(BASE_DIR, ".env.json"), "r") as file:
    ENV = json.load(file)

INDEX_STATE_PATH = Path(BASE_DIR) / "index_state.json"
VAULT_DIR = ENV["VAULT"]
DB_PATH = DB_PATH = Path(BASE_DIR) / "chroma.db"

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

# Shared mutable reference: watcher thread writes, stream_answer reads
_vs_box = {"vectorstore":None}
_vs_lock = threading.Lock()

# index state helpers
def _load_state():
    if not INDEX_STATE_PATH.exists():
        return None
    with open(INDEX_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
    
def _save_state(files_state):
    with open(INDEX_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(
                {"files": files_state}, 
                f, indent=2
        )

def _indexed_files(state):
    if not state:
        return {}
    return state.get("files", {})

def _file_state(filepath):
    s = Path(filepath).stat()
    return {
        "mtime_ns": s.st_mtime_ns, 
        "size": s.st_size
    }
    
def _load_vs():
    return Chroma(
        persist_directory = str(DB_PATH),
        embedding_function = embedding
    )

# Sync function

def _sync(state):
    print("[watcher] Syncing vault changes")
    previous = _indexed_files(state)
    current = dict(previous)
    seen = set()
    vault = Path(VAULT_DIR)
    vs = _load_vs()
    
    for root, _, files in os.walk(VAULT_DIR):
        for filename in files:
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(root, filename)
            rel = Path(filepath).relative_to(vault).as_posix()
            seen.add(rel)
            
            docs = load_file(filepath)
            if not docs:
                continue
                
            fstate = _file_state(filepath)
            fhash = docs[0].metadata.get("content_hash")
            prev = previous.get(rel, {})
            
            # Skip unchanged files
            if (prev.get("hash") == fhash and
                    prev.get("mtime_ns") == fstate["mtime_ns"] and
                    prev.get("size") == fstate["size"]):
                current[rel] = {**prev, **fstate}
                continue

            chunks = chunk(docs)
            if not chunks:
                continue
        
            ids = [f"{rel}:{fhash}:{i}" for i in range(len(chunks))]
            old_ids = prev.get("ids", [])
            
            try:
                vs.add_documents(chunks, ids = ids)
            except Exception as e:
                print(f"[watcher] Embedding failed for {filepath} : {e}")
                continue
            
            if old_ids:
                try:
                    vs.delete(ids=old_ids)
                except Exception as e:
                    print(f"[watcher] Could not remove stale chunks: {e}")
            
            current[rel] = {
                "hash": fhash, 
                **fstate,
                "ids": ids
            }
            print(f"[watcher] Updated: {filepath}")
            
    # Handle deleted files
    for rel in set(previous) - seen:
        old_ids = previous[rel].get("ids", [])
        if old_ids:
            try:
                vs.delete(ids=old_ids)
            except Exception as e:
                print(f"[watcher] Could not remove deleted file chunks: {e}")
            current.pop(rel, None)
            print(f"[watcher] Removed: {rel}")
            
    _save_state(current)
    print(f"[watcher] Sync done. {len(current)} files tracked.")
    return vs
    
    
# Background watcher thread
def _watch_loop():
    print(f"[watcher] Watching {VAULT_DIR} for changes...")
    for _ in watch(VAULT_DIR):
        new_vs = _sync(_load_state())
        with _vs_lock:
            _vs_box["vectorstore"] = new_vs

def _start_watcher():
    t=threading.Thread(target=_watch_loop, daemon=True)
    t.start()
    
    
# Startup
def init(force_reindex=False):
    '''Call once at app startup'''
    state = _load_state()
    
    if force_reindex or not DB_PATH.exists() or not state:
        # reuse main.py build_index by just doing a full sync with empty state
        vs = _sync({})
    else:
        vs = _sync(state)
    
    with _vs_lock:
        _vs_box["vectorstore"] = vs
        
    _start_watcher()

def stream_answer(query: str, history=None):
    """Yield {"sources": [...]} once, then {"token": ...} events.

    `history` is the chat's earlier messages (see chat_store.get_messages).
    """
    with _vs_lock:
        vs = _vs_box["vectorstore"]

    if vs is None:
        yield {"token": "Still indexing your vault, please wait a moment and try again."}
        return

    # In a conversation, retrieve with a standalone rewrite of the question (made in the same
    # LLM call as the paraphrases) so follow-ups like "show me all of it" find the right notes
    transcript = format_history(history) if history else None
    queries = generate_queries(query, model, transcript) if transcript else None
    standalone = queries[0] if queries else query

    # Notes the question names or dates ("20 july 2026") are sent whole; otherwise, or if they're
    # too large, fall back to search (limited to those notes when there are any)
    targets = find_target_notes(vs, standalone) or (
        find_target_notes(vs, query) if standalone != query else []
    )
    docs = load_whole_files(vs, targets) if targets else None

    if not docs:
        retriever = retrieve(vs, standalone, targets)
        docs = rag_fusion_retrieve(queries or generate_queries(standalone, model), retriever)

    yield {"sources": list(dict.fromkeys(doc.metadata.get("filename") for doc in docs))}

    for chunk_text in generation(docs, model, query, transcript, stream=True):
        yield {"token": chunk_text}