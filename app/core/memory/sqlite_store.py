"""
SQLite-backed Conversation Store — persistent multi-turn session management.

Drop-in replacement for the in-memory ConversationStore.
Sessions survive restarts; old sessions are cleaned up by TTL.
"""
from __future__ import annotations

import json
import time
import uuid
import logging
import aiosqlite
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MAX_TURNS = 50
DEFAULT_TTL_SECONDS = 86400  # 24 hours for persistent store


class SQLiteConversationStore:
    """
    SQLite-backed conversation store. API-compatible with ConversationStore.

    Usage:
        store = SQLiteConversationStore("./data/conversations.db")
        await store.initialize()
        sid = await store.get_or_create("session-123")
        await store.add_message(sid, "user", "Hello")
        history = await store.get_history(sid)
    """

    def __init__(
        self,
        db_path: str = "./data/conversations.db",
        max_turns: int = DEFAULT_MAX_TURNS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self.db_path = db_path
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds
        self._db: aiosqlite.Connection | None = None

    async def initialize(self):
        """Create DB and tables if needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                last_active REAL NOT NULL
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        await self._db.commit()
        await self._cleanup_expired()
        logger.info(f"SQLite conversation store initialized: {self.db_path}")

    async def get_or_create(self, session_id: str | None = None) -> str:
        """Get existing session or create a new one."""
        assert self._db
        sid = session_id or str(uuid.uuid4())

        row = await self._db.execute_fetchall(
            "SELECT session_id FROM sessions WHERE session_id = ?", (sid,)
        )
        if row:
            await self._db.execute(
                "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                (time.time(), sid),
            )
        else:
            now = time.time()
            await self._db.execute(
                "INSERT INTO sessions (session_id, created_at, last_active) VALUES (?, ?, ?)",
                (sid, now, now),
            )
        await self._db.commit()
        return sid

    async def add_message(self, session_id: str, role: str, content: str):
        """Add a message, trimming old ones if over max_turns."""
        assert self._db

        # Ensure session exists
        row = await self._db.execute_fetchall(
            "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
        )
        if not row:
            now = time.time()
            await self._db.execute(
                "INSERT INTO sessions (session_id, created_at, last_active) VALUES (?, ?, ?)",
                (session_id, now, now),
            )

        await self._db.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, time.time()),
        )
        await self._db.execute(
            "UPDATE sessions SET last_active = ? WHERE session_id = ?",
            (time.time(), session_id),
        )

        # Trim oldest messages if over limit
        count_rows = await self._db.execute_fetchall(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        )
        count = count_rows[0][0] if count_rows else 0
        if count > self.max_turns:
            overflow = count - self.max_turns
            await self._db.execute(
                """DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages WHERE session_id = ?
                    ORDER BY id ASC LIMIT ?
                )""",
                (session_id, overflow),
            )

        await self._db.commit()

    async def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        assert self._db
        rows = await self._db.execute_fetchall(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        return [{"role": r[0], "content": r[1]} for r in rows]

    async def clear_session(self, session_id: str):
        """Clear a specific session."""
        assert self._db
        await self._db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self._db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await self._db.commit()

    async def session_count(self) -> int:
        assert self._db
        rows = await self._db.execute_fetchall("SELECT COUNT(*) FROM sessions")
        return rows[0][0] if rows else 0

    async def _cleanup_expired(self):
        """Remove expired sessions."""
        assert self._db
        cutoff = time.time() - self.ttl_seconds
        expired = await self._db.execute_fetchall(
            "SELECT session_id FROM sessions WHERE last_active < ?", (cutoff,)
        )
        for (sid,) in expired:
            await self._db.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
            await self._db.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
        if expired:
            await self._db.commit()
            logger.debug(f"Cleaned up {len(expired)} expired sessions")

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
