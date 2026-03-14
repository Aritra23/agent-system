import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "tasks.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                task      TEXT    NOT NULL,
                output    TEXT,
                error     TEXT,
                tools_used TEXT NOT NULL DEFAULT '[]',
                steps     TEXT NOT NULL DEFAULT '[]',
                timestamp TEXT NOT NULL
            )
        """)
        conn.commit()


def save_task(task: str, output, error: str | None, tools_used: list[str], steps: list[str], timestamp: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (task, output, error, tools_used, steps, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task,
                json.dumps(output) if output is not None else None,
                error,
                json.dumps(tools_used),
                json.dumps(steps),
                timestamp,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_tasks(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_task_by_id(task_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        result = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return result.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["tools_used"] = json.loads(d["tools_used"])
    d["steps"] = json.loads(d["steps"])
    if d["output"] is not None:
        try:
            d["output"] = json.loads(d["output"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d
