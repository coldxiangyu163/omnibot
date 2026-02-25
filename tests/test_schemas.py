"""Tests for Pydantic schemas."""
import pytest
from datetime import datetime
from app.schemas.message import BotMessage, BotResponse
from app.schemas.tool import ToolInfo, AgentRequest, AgentStepInfo, AgentResponse


class TestBotMessage:
    def test_defaults(self):
        msg = BotMessage(text="hello")
        assert msg.channel == "web"
        assert msg.sender_id == "anonymous"
        assert msg.session_id is None
        assert msg.timestamp is None
        assert msg.metadata is None

    def test_full_fields(self):
        now = datetime.now()
        msg = BotMessage(
            channel="slack", sender_id="user-1", text="hi",
            session_id="s1", timestamp=now, metadata={"key": "val"},
        )
        assert msg.channel == "slack"
        assert msg.sender_id == "user-1"
        assert msg.session_id == "s1"
        assert msg.metadata == {"key": "val"}


class TestBotResponse:
    def test_defaults(self):
        resp = BotResponse(text="answer")
        assert resp.text == "answer"
        assert resp.sources is None
        assert resp.session_id is None
        assert resp.tool_calls_count == 0
        assert resp.agent_steps == 0

    def test_with_sources(self):
        resp = BotResponse(text="ok", sources=["doc1.pdf"], session_id="s1",
                           tool_calls_count=2, agent_steps=3)
        assert resp.sources == ["doc1.pdf"]
        assert resp.tool_calls_count == 2


class TestToolSchemas:
    def test_tool_info(self):
        t = ToolInfo(name="search", description="Search tool", source="mcp")
        assert t.name == "search"
        assert t.input_schema == {}

    def test_agent_request_defaults(self):
        req = AgentRequest(message="hello")
        assert req.system_prompt is None
        assert req.conversation is None
        assert req.max_iterations == 10

    def test_agent_request_with_conversation(self):
        req = AgentRequest(
            message="follow up",
            conversation=[{"role": "user", "content": "first"}],
            max_iterations=5,
        )
        assert len(req.conversation) == 1
        assert req.max_iterations == 5

    def test_agent_step_info(self):
        step = AgentStepInfo(step_number=1, reasoning="thinking",
                             tool_calls=[{"tool": "x"}], response="done")
        assert step.step_number == 1
        assert len(step.tool_calls) == 1

    def test_agent_response(self):
        resp = AgentResponse(response="answer", total_tool_calls=2,
                             total_duration_ms=500)
        assert resp.response == "answer"
        assert resp.steps == []
