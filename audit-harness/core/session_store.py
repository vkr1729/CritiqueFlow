import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DB_DIR = Path(__file__).parent.parent / "data"
_DB_PATH = _DB_DIR / "sessions.db"


def init_db() -> str:
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    db_path_str = str(_DB_PATH)
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                folder_path TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                chain_json TEXT NOT NULL,
                is_complete INTEGER DEFAULT 0,
                summary TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_text TEXT NOT NULL,
                source_session_ids TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.commit()
    logger.info("Session database initialized at %s", db_path_str)
    return db_path_str


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_session(session_id: str, title: str, folder_path: str,
                 chain_dict: dict, is_complete: bool = False,
                 summary: str = ""):
    chain_json = json.dumps(chain_dict)
    now = _now()
    with _get_connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if existing:
            created_at = existing["created_at"]
        else:
            created_at = now
        conn.execute("""
            INSERT OR REPLACE INTO sessions
            (id, title, folder_path, created_at, updated_at, chain_json, is_complete, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, title, folder_path, created_at, now, chain_json,
              int(is_complete), summary))
        conn.commit()


def load_session(session_id: str) -> dict:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Session not found: {session_id}")
        result = dict(row)
        result["chain"] = json.loads(result["chain_json"])
        return result


def list_sessions(limit: int = 50, offset: int = 0) -> list[dict]:
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, folder_path, created_at, updated_at, is_complete "
            "FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_session(session_id: str):
    with _get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()


def clear_all_sessions():
    with _get_connection() as conn:
        conn.execute("DELETE FROM sessions")
        conn.commit()


def enforce_session_cap(max_sessions: int):
    with _get_connection() as conn:
        conn.execute("""
            DELETE FROM sessions WHERE id NOT IN (
                SELECT id FROM sessions ORDER BY updated_at DESC LIMIT ?
            )
        """, (max_sessions,))


def save_learned_skill(skill_text: str, source_session_ids: str = "") -> int:
    now = _now()
    with _get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO learned_skills (skill_text, source_session_ids, created_at, is_active) "
            "VALUES (?, ?, ?, 1)",
            (skill_text, source_session_ids, now)
        )
        conn.commit()
        return cur.lastrowid


def list_learned_skills(active_only: bool = True) -> list[dict]:
    with _get_connection() as conn:
        if active_only:
            rows = conn.execute(
                "SELECT * FROM learned_skills WHERE is_active = 1 ORDER BY id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM learned_skills ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]


def update_learned_skill(skill_id: int, skill_text: str = None, is_active: bool = None):
    updates = []
    params = []
    if skill_text is not None:
        updates.append("skill_text = ?")
        params.append(skill_text)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(int(is_active))
    if not updates:
        return
    params.append(skill_id)
    with _get_connection() as conn:
        conn.execute(
            f"UPDATE learned_skills SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )
        conn.commit()


def delete_learned_skill(skill_id: int):
    with _get_connection() as conn:
        conn.execute("DELETE FROM learned_skills WHERE id = ?", (skill_id,))
        conn.commit()
