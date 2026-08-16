"""
SQLite persistence for Nexus AI.

Logs every query + its final LLM3-synthesized answer, plus the underlying
debate transcript summary, for history/telemetry.
"""

import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "nexus_ai.db"


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
        conn.commit()


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
                datetime.datetime.now().isoformat(timespec="seconds"),
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
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM answers ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]