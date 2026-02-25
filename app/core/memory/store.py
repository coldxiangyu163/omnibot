"""
Conversation Store — in-memory multi-turn session management.

Stores conversation history per session_id with TTL-based expiration.
"""
from __future__ import annotations

import time
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_MAX_TURNS = 50  # max messages per session
DEFAULT_TTL_SECONDS = 3600  # 1 hour


@dataclass
class Session:
    """A single conversation session."""
    session_id: str
    messages: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.last_active = time.time()

    def get_history(self) -> list[dict]:
        return list(self.messages)

    def is_expired(self, ttl: int) -> bool:
        return (time.time() - self.last_active) > ttl


class ConversationStore:
    """
    In-memory conversation store with TTL cleanup.

    Usage:
        store = ConversationStore()
        sid = store.get_or_create("session-123")
        store.add_message(sid, "user", "Hello")
        store.add_message(sid, "assistant", "Hi there!")
        history = store.get_history(sid)
    """

    def __init__(
        self,
        max_turns: int = DEFAULT_MAX_TURNS,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self._sessions: dict[str, Session] = {}
        self.max_turns = max_turns
        self.ttl_seconds = ttl_seconds

    def get_or_create(self, session_id: str | None = None) -> str:
        """Get existing session or create a new one. Returns session_id."""
        self._cleanup_expired()

        if session_id and session_id in self._sessions:
            return session_id

        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = Session(session_id=sid)
        logger.debug(f"Created new session: {sid}")
        return sid

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the session, trimming old messages if over max_turns."""
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)

        session = self._sessions[session_id]
        session.add_message(role, content)

        # Trim oldest messages if exceeding max_turns (keep system prompt if present)
        if len(session.messages) > self.max_turns:
            overflow = len(session.messages) - self.max_turns
            session.messages = session.messages[overflow:]

    def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        if session_id not in self._sessions:
            return []
        return self._sessions[session_id].get_history()

    def clear_session(self, session_id: str):
        """Clear a specific session."""
        self._sessions.pop(session_id, None)

    def session_count(self) -> int:
        return len(self._sessions)

    def _cleanup_expired(self):
        """Remove expired sessions."""
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(self.ttl_seconds)
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions")
