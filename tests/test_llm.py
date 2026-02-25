"""Tests for LLM providers (mocked, no real API calls)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.llm.base import LLMProvider


class TestLLMProviderBase:
    """Test the base class fallback streaming."""

    @pytest.mark.asyncio
    async def test_stream_fallback_text_only(self):
        """Default stream implementation falls back to non-streaming."""
        provider = LLMProvider.__new__(LLMProvider)
        provider.generate_with_tools = AsyncMock(return_value={
            "content": "Hello world",
            "tool_calls": None,
        })

        chunks = []
        async for chunk in provider.generate_with_tools_stream(
            messages=[{"role": "user", "content": "hi"}]
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == {"type": "content_delta", "delta": "Hello world"}
        assert chunks[1] == {"type": "done", "content": "Hello world"}

    @pytest.mark.asyncio
    async def test_stream_fallback_with_tools(self):
        """Default stream fallback emits tool_calls then done."""
        provider = LLMProvider.__new__(LLMProvider)
        tool_calls = [{"id": "c1", "function": {"name": "search", "arguments": "{}"}}]
        provider.generate_with_tools = AsyncMock(return_value={
            "content": None,
            "tool_calls": tool_calls,
        })

        chunks = []
        async for chunk in provider.generate_with_tools_stream(
            messages=[{"role": "user", "content": "search"}]
        ):
            chunks.append(chunk)

        assert chunks[0]["type"] == "tool_calls"
        assert chunks[0]["tool_calls"] == tool_calls
        assert chunks[-1]["type"] == "done"


class TestOpenAIProvider:
    @pytest.mark.asyncio
    async def test_generate(self):
        with patch("app.core.llm.openai_provider.AsyncOpenAI") as MockClient:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "test response"

            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            with patch("app.config.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.llm_model = "gpt-4o"
                from app.core.llm.openai_provider import OpenAIProvider
                provider = OpenAIProvider()
                provider.client = mock_client

            result = await provider.generate("hello", system="be helpful")
            assert result == "test response"

    @pytest.mark.asyncio
    async def test_generate_with_tools_no_calls(self):
        with patch("app.core.llm.openai_provider.AsyncOpenAI") as MockClient:
            mock_msg = MagicMock()
            mock_msg.content = "plain answer"
            mock_msg.tool_calls = None

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = mock_msg

            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            with patch("app.config.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.llm_model = "gpt-4o"
                from app.core.llm.openai_provider import OpenAIProvider
                provider = OpenAIProvider()
                provider.client = mock_client

            result = await provider.generate_with_tools(
                messages=[{"role": "user", "content": "hi"}]
            )
            assert result["content"] == "plain answer"
            assert result["tool_calls"] is None

    @pytest.mark.asyncio
    async def test_generate_with_tools_has_calls(self):
        with patch("app.core.llm.openai_provider.AsyncOpenAI") as MockClient:
            mock_tc = MagicMock()
            mock_tc.id = "call_1"
            mock_tc.function.name = "search"
            mock_tc.function.arguments = '{"q": "test"}'

            mock_msg = MagicMock()
            mock_msg.content = None
            mock_msg.tool_calls = [mock_tc]

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = mock_msg

            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            with patch("app.config.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.llm_model = "gpt-4o"
                from app.core.llm.openai_provider import OpenAIProvider
                provider = OpenAIProvider()
                provider.client = mock_client

            result = await provider.generate_with_tools(
                messages=[{"role": "user", "content": "search"}],
                tools=[{"type": "function", "function": {"name": "search"}}],
            )
            assert result["tool_calls"] is not None
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["function"]["name"] == "search"
