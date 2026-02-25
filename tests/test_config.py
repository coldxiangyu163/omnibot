"""Tests for application config."""
import pytest
from app.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.llm_provider == "openai"
        assert s.llm_model == "gpt-4o"
        assert s.max_agent_iterations == 10
        assert s.host == "0.0.0.0"
        assert s.port == 8000

    def test_custom_values(self):
        s = Settings(
            llm_provider="anthropic",
            llm_model="claude-3-opus",
            max_agent_iterations=5,
        )
        assert s.llm_provider == "anthropic"
        assert s.llm_model == "claude-3-opus"
        assert s.max_agent_iterations == 5
