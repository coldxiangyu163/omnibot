"""Tests for AgentEngine integration."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.engine import AgentEngine
from app.schemas.message import BotMessage


class TestAgentEngine:
    @pytest.fixture
    def engine(self):
        """Create engine with mocked LLM (no real API calls)."""
        with patch("app.core.engine.OpenAIProvider") as MockProvider:
            mock_llm = AsyncMock()
            mock_llm.generate_with_tools = AsyncMock(return_value={
                "content": "Mocked response",
                "tool_calls": None,
            })
            MockProvider.return_value = mock_llm

            e = AgentEngine()
            e.llm = mock_llm
            e._initialized = True
            return e

    @pytest.mark.asyncio
    async def test_chat_basic(self, engine):
        msg = BotMessage(text="hello")
        resp = await engine.chat(msg)
        assert resp.text == "Mocked response"
        assert resp.session_id is not None
        assert resp.agent_steps >= 1

    @pytest.mark.asyncio
    async def test_chat_session_continuity(self, engine):
        """Same session_id should accumulate history."""
        msg1 = BotMessage(text="first message", session_id="test-session")
        resp1 = await engine.chat(msg1)
        assert resp1.session_id == "test-session"

        msg2 = BotMessage(text="second message", session_id="test-session")
        resp2 = await engine.chat(msg2)
        assert resp2.session_id == "test-session"

        # Verify history accumulated
        history = engine.conversations.get_history("test-session")
        assert len(history) == 4  # user, assistant, user, assistant

    @pytest.mark.asyncio
    async def test_chat_different_sessions_isolated(self, engine):
        await engine.chat(BotMessage(text="hi", session_id="s1"))
        await engine.chat(BotMessage(text="hi", session_id="s2"))

        h1 = engine.conversations.get_history("s1")
        h2 = engine.conversations.get_history("s2")
        assert len(h1) == 2  # user + assistant
        assert len(h2) == 2

    @pytest.mark.asyncio
    async def test_run_agent_basic(self, engine):
        result = await engine.run_agent(message="test")
        assert result.response == "Mocked response"
        assert result.total_tool_calls == 0

    @pytest.mark.asyncio
    async def test_run_agent_with_session(self, engine):
        r1 = await engine.run_agent(message="first", session_id="agent-s1")
        r2 = await engine.run_agent(message="second", session_id="agent-s1")

        history = engine.conversations.get_history("agent-s1")
        assert len(history) == 4

    @pytest.mark.asyncio
    async def test_run_agent_explicit_conversation_overrides_session(self, engine):
        """Explicit conversation param should take precedence over session."""
        custom_conv = [{"role": "user", "content": "custom context"}]
        result = await engine.run_agent(
            message="follow up",
            conversation=custom_conv,
            session_id="should-not-use",
        )
        assert result.response == "Mocked response"
        # Session should NOT have been created since explicit conversation was passed
        history = engine.conversations.get_history("should-not-use")
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_chat_auto_generates_session_id(self, engine):
        msg = BotMessage(text="no session")
        resp = await engine.chat(msg)
        assert resp.session_id is not None
        assert len(resp.session_id) > 0
