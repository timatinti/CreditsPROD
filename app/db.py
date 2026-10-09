import json
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .security import decrypt_payload, encrypt_payload, hash_secret, new_session_token, token_hash, verify_secret

DB_PATH = Path(__file__).resolve().parent.parent / "drafts.sqlite3"
_lock = threading.RLock()
SESSION_DAYS = 7


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    with _lock, connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, client_id TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS sessions (session_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at)")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(drafts)").fetchall()}
        if columns and "token_hash" in columns:
            conn.execute("ALTER TABLE drafts RENAME TO drafts_legacy")
            columns = set()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                client_id TEXT NOT NULL UNIQUE,
                encrypted_payload TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        if "token_hash" not in columns and conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='drafts_legacy'").fetchone():
            conn.execute("INSERT OR IGNORE INTO drafts (id, client_id, encrypted_payload, version, updated_at) SELECT id, client_id, encrypted_payload, version, updated_at FROM drafts_legacy")
            conn.execute("DROP TABLE drafts_legacy")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_drafts_updated ON drafts(updated_at)")


def create_user(client_id: str, password: str) -> bool:
    try:
        with _lock, connect() as conn:
            conn.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (str(uuid.uuid4()), client_id, hash_secret(password), _now()))
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate_user(client_id: str, password: str) -> tuple[str, str] | None:
    with connect() as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE client_id = ?", (client_id,)).fetchone()
    if not row or not verify_secret(password, row["password_hash"]):
        return None
    raw_token = new_session_token()
    with _lock, connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (_now(),))
        conn.execute("INSERT INTO sessions VALUES (?, ?, ?)", (token_hash(raw_token), row["id"], (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()))
    return raw_token, client_id


def user_by_session(raw_token: str | None) -> str | None:
    if not raw_token:
        return None
    with connect() as conn:
        row = conn.execute("""
            SELECT u.client_id FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.session_hash=? AND s.expires_at > ?
        """, (token_hash(raw_token), _now())).fetchone()
    return row["client_id"] if row else None


def delete_session(raw_token: str | None) -> None:
    if raw_token:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_hash=?", (token_hash(raw_token),))


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {"id": row["id"], "client_id": row["client_id"], "fields": json.loads(decrypt_payload(row["encrypted_payload"])), "version": row["version"], "updated_at": row["updated_at"]}


def get_draft(client_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM drafts WHERE client_id=?", (client_id,)).fetchone()
    return _row_to_dict(row) if row else None


def ensure_draft(client_id: str) -> dict[str, Any]:
    existing = get_draft(client_id)
    if existing:
        return existing
    now = _now()
    with _lock, connect() as conn:
        conn.execute("INSERT OR IGNORE INTO drafts VALUES (?, ?, ?, 0, ?)", (str(uuid.uuid4()), client_id, encrypt_payload("{}"), now))
    return get_draft(client_id)


def patch_draft(client_id: str, field: str, value: Any, expected_version: int) -> dict[str, Any] | None:
    with _lock, connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM drafts WHERE client_id=?", (client_id,)).fetchone()
        if not row or row["version"] != expected_version:
            conn.rollback()
            return None
        fields = json.loads(decrypt_payload(row["encrypted_payload"]))
        fields[field] = value
        conn.execute("UPDATE drafts SET encrypted_payload=?, version=version+1, updated_at=? WHERE client_id=? AND version=?", (encrypt_payload(json.dumps(fields)), _now(), client_id, expected_version))
        updated = conn.execute("SELECT * FROM drafts WHERE client_id=?", (client_id,)).fetchone()
        conn.commit()
    return _row_to_dict(updated)


def list_drafts() -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute("SELECT id, client_id, version, updated_at FROM drafts ORDER BY updated_at DESC").fetchall()
    return [dict(row) for row in rows]


def delete_draft(draft_id: str) -> bool:
    with _lock, connect() as conn:
        result = conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
    return result.rowcount > 0
