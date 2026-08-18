"""SQLite persistence for multi-turn Nexus AI chats."""

import datetime as dt
import sqlite3
import uuid
from pathlib import Path


DB_PATH = Path(__file__).parent / "nexus_ai.db"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_query TEXT NOT NULL,
                clarification_answers TEXT,
                option_a_json TEXT NOT NULL,
                option_b_json TEXT NOT NULL,
                final_recommendation TEXT NOT NULL,
                synthesis_json TEXT NOT NULL,
                rounds_run INTEGER NOT NULL,
                converged INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, id)")
        conn.commit()


def create_chat(title: str = "New chat") -> str:
    chat_id = str(uuid.uuid4())
    now = _now()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO chats (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (chat_id, title[:80] or "New chat", now, now),
        )
        conn.commit()
    return chat_id


def rename_chat(chat_id: str, title: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
            (title[:80] or "New chat", _now(), chat_id),
        )
        conn.commit()


def delete_chat(chat_id: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        conn.commit()


def list_chats(limit: int = 50) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM chats ORDER BY updated_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_message(chat_id: str, role: str, content: str) -> None:
    if role not in {"user", "assistant"}:
        raise ValueError("role must be 'user' or 'assistant'")
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, _now()),
        )
        conn.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (_now(), chat_id))
        conn.commit()


def get_messages(chat_id: str) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def log_answer(
    user_query: str,
    clarification_answers: str,
    option_a_json: str,
    option_b_json: str,
    final_recommendation: str,
    synthesis_json: str,
    rounds_run: int,
    converged: bool,
) -> None:
    """Legacy telemetry function retained for existing callers."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO answers (
                timestamp, user_query, clarification_answers,
                option_a_json, option_b_json,
                final_recommendation, synthesis_json,
                rounds_run, converged
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                user_query,
                clarification_answers,
                option_a_json,
                option_b_json,
                final_recommendation,
                synthesis_json,
                rounds_run,
                int(converged),
            ),
        )
        conn.commit()


def fetch_recent(limit: int = 20) -> list[dict]:
    """Legacy history function retained for compatibility."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM answers ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
