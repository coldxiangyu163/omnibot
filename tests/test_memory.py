"""Tests for conversation memory store."""
import time
import pytest
from app.core.memory.store import ConversationStore, Session


class TestSession:
    def test_create_session(self):
        s = Session(session_id="test-1")
        assert s.session_id == "test-1"
        assert s.messages == []

    def test_add_message(self):
        s = Session(session_id="test-1")
        s.add_message("user", "hello")
        s.add_message("assistant", "hi there")
        assert len(s.messages) == 2
        assert s.messages[0] == {"role": "user", "content": "hello"}
        assert s.messages[1] == {"role": "assistant", "content": "hi there"}

    def test_get_history_returns_copy(self):
        s = Session(session_id="test-1")
        s.add_message("user", "hello")
        history = s.get_history()
        history.append({"role": "user", "content": "injected"})
        assert len(s.messages) == 1  # original unchanged

    def test_expired(self):
        s = Session(session_id="test-1")
        s.last_active = time.time() - 7200  # 2 hours ago
        assert s.is_expired(3600) is True
        assert s.is_expired(86400) is False


class TestConversationStore:
    def test_create_new_session(self):
        store = ConversationStore()
        sid = store.get_or_create()
        assert sid is not None
        assert store.session_count() == 1

    def test_get_existing_session(self):
        store = ConversationStore()
        sid = store.get_or_create("my-session")
        sid2 = store.get_or_create("my-session")
        assert sid == sid2
        assert store.session_count() == 1

    def test_add_and_get_history(self):
        store = ConversationStore()
        sid = store.get_or_create("s1")
        store.add_message(sid, "user", "What is MCP?")
        store.add_message(sid, "assistant", "Model Context Protocol.")
        store.add_message(sid, "user", "Tell me more.")
        history = store.get_history(sid)
        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[2]["content"] == "Tell me more."

    def test_max_turns_trimming(self):
        store = ConversationStore(max_turns=4)
        sid = store.get_or_create("s1")
        for i in range(6):
            store.add_message(sid, "user", f"msg-{i}")
        history = store.get_history(sid)
        assert len(history) == 4
        assert history[0]["content"] == "msg-2"  # oldest trimmed

    def test_get_history_unknown_session(self):
        store = ConversationStore()
        assert store.get_history("nonexistent") == []

    def test_clear_session(self):
        store = ConversationStore()
        sid = store.get_or_create("s1")
        store.add_message(sid, "user", "hello")
        store.clear_session(sid)
        assert store.session_count() == 0
        assert store.get_history(sid) == []

    def test_ttl_cleanup(self):
        store = ConversationStore(ttl_seconds=1)
        sid = store.get_or_create("old-session")
        store.add_message(sid, "user", "hello")
        # Manually expire it
        store._sessions[sid].last_active = time.time() - 10
        # Trigger cleanup via get_or_create
        store.get_or_create("new-session")
        assert "old-session" not in store._sessions
        assert store.session_count() == 1

    def test_add_message_auto_creates_session(self):
        store = ConversationStore()
        store.add_message("auto-created", "user", "hello")
        assert store.session_count() == 1
        assert store.get_history("auto-created")[0]["content"] == "hello"

    def test_multiple_sessions_isolated(self):
        store = ConversationStore()
        store.add_message("s1", "user", "hello from s1")
        store.add_message("s2", "user", "hello from s2")
        assert len(store.get_history("s1")) == 1
        assert len(store.get_history("s2")) == 1
        assert store.get_history("s1")[0]["content"] == "hello from s1"
        assert store.get_history("s2")[0]["content"] == "hello from s2"
