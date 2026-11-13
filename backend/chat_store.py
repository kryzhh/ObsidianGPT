import json
import sqlite3
import time
import uuid
from contextlib import closing
from pathlib import Path

# Lives next to chroma.db; contains note excerpts, so it's gitignored
DB_PATH = Path(__file__).resolve().parent.parent / "chats.db"

TITLE_MAX_CHARS = 60


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(_connect()) as conn, conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                created_at  REAL NOT NULL,
                updated_at  REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                role        TEXT NOT NULL,
                content     TEXT NOT NULL,
                sources     TEXT NOT NULL DEFAULT '[]',
                created_at  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id);
        """)


# Title is the first question, trimmed at a word boundary. No LLM call, so it's instant.
def _title_from(question):
    title = " ".join(question.split())
    if len(title) > TITLE_MAX_CHARS:
        title = title[:TITLE_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return title


def _chat_dict(row):
    return {"id": row["id"], "title": row["title"], "updated_at": row["updated_at"]}


def create_chat(first_question):
    now = time.time()
    chat = {"id": uuid.uuid4().hex, "title": _title_from(first_question), "updated_at": now}
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO chats (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (chat["id"], chat["title"], now, now),
        )
    return chat


def get_chat(chat_id):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM chats WHERE id = ?", (chat_id,)).fetchone()
    return _chat_dict(row) if row else None


# Chats whose only exchange failed have no messages left, so they're hidden
def list_chats():
    with closing(_connect()) as conn:
        rows = conn.execute("""
            SELECT * FROM chats c
            WHERE EXISTS (SELECT 1 FROM messages m WHERE m.chat_id = c.id)
            ORDER BY updated_at DESC
        """).fetchall()
    return [_chat_dict(row) for row in rows]


def get_messages(chat_id, limit=None):
    """Messages in chronological order. `limit` keeps only the most recent ones."""
    query = "SELECT role, content, sources FROM messages WHERE chat_id = ? ORDER BY id DESC"
    params = (chat_id,)
    if limit:
        query += " LIMIT ?"
        params += (limit,)

    with closing(_connect()) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {"role": row["role"], "content": row["content"], "sources": json.loads(row["sources"])}
        for row in reversed(rows)
    ]


def add_message(chat_id, role, content, sources=None):
    now = time.time()
    with closing(_connect()) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO messages (chat_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?)",
            (chat_id, role, content, json.dumps(sources or []), now),
        )
        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
    return cursor.lastrowid


def delete_message(message_id):
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))


def delete_chat(chat_id):
    with closing(_connect()) as conn, conn:
        deleted = conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,)).rowcount
    return deleted > 0
