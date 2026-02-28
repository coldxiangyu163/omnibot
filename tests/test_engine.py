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
        assert resp.agent_steps >= 1

    @pytest.mark.asyncio
    async def test_chat_preserves_session_id(self, engine):
        msg = BotMessage(text="hello", session_id="s1")
        resp = await engine.chat(msg)
        assert resp.session_id == "s1"

    @pytest.mark.asyncio
    async def test_chat_no_session_auto_creates(self, engine):
        msg = BotMessage(text="hello")
        resp = await engine.chat(msg)
        assert resp.session_id is not None  # auto-created

    @pytest.mark.asyncio
    async def test_chat_no_tool_calls(self, engine):
        msg = BotMessage(text="hello")
        resp = await engine.chat(msg)
        assert resp.tool_calls_count == 0
        assert resp.sources is None

    @pytest.mark.asyncio
    async def test_run_agent_basic(self, engine):
        result = await engine.run_agent(message="test")
        assert result.response == "Mocked response"
        assert result.total_tool_calls == 0

    @pytest.mark.asyncio
    async def test_run_agent_custom_system_prompt(self, engine):
        result = await engine.run_agent(
            message="test",
            system_prompt="You are a pirate.",
        )
        assert result.response == "Mocked response"

    @pytest.mark.asyncio
    async def test_run_agent_with_conversation(self, engine):
        conv = [{"role": "user", "content": "context"}]
        result = await engine.run_agent(message="follow up", conversation=conv)
        assert result.response == "Mocked response"

    @pytest.mark.asyncio
    async def test_run_agent_max_iterations(self, engine):
        result = await engine.run_agent(message="test", max_iterations=3)
        assert result.response == "Mocked response"
