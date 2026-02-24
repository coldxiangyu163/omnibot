"""Pydantic models for tools and agent."""
from pydantic import BaseModel
from typing import Any


class ToolInfo(BaseModel):
    """Tool information returned by the API."""
    name: str
    description: str
    source: str  # "mcp" or "builtin"
    input_schema: dict[str, Any] = {}


class AgentRequest(BaseModel):
    """Request to run the agent directly."""
    message: str
    system_prompt: str | None = None
    conversation: list[dict] | None = None
    max_iterations: int = 10


class AgentStepInfo(BaseModel):
    step_number: int
    reasoning: str | None = None
    tool_calls: list[dict] = []
    response: str | None = None


class AgentResponse(BaseModel):
    """Full agent response with step details."""
    response: str
    steps: list[AgentStepInfo] = []
    total_tool_calls: int = 0
    total_duration_ms: int = 0
