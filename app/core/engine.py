"""
AgentEngine — the heart of OmniBot.

Wires together: LLM providers + MCP tool registry + Agent loop + RAG (as built-in tool).
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from app.core.llm.base import LLMProvider
from app.core.llm.openai_provider import OpenAIProvider
from app.core.llm.anthropic_provider import AnthropicProvider
from app.core.mcp.registry import ToolRegistry
from app.core.agent.loop import AgentLoop, AgentResult
from app.core.rag.pipeline import RAGPipeline
from app.core.memory.store import ConversationStore
from app.schemas.message import BotMessage, BotResponse
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are OmniBot, an AI agent with access to external tools.

When a user asks a question:
1. Think about whether you need to use any tools to answer it.
2. If tools are available and relevant, use them.
3. Synthesize the results into a clear, helpful response.
4. If no tools are needed, answer directly from your knowledge.

Be concise, accurate, and helpful."""


class AgentEngine:
    """
    Core engine that orchestrates the agent loop.

    Supports two modes:
    - Agent mode (default): LLM + tools via ReAct loop
    - Simple mode: Direct LLM call (backward compatible, no tools)
    """

    def __init__(self):
        self.llm: LLMProvider = self._init_llm()
        self.registry: ToolRegistry = ToolRegistry()
        self.rag: RAGPipeline = RAGPipeline()
        self.conversations = self._init_memory()
        self.system_prompt: str = DEFAULT_SYSTEM_PROMPT
        self._initialized = False

    def _init_llm(self) -> LLMProvider:
        if settings.llm_provider == "anthropic":
            return AnthropicProvider()
        return OpenAIProvider()

    def _init_memory(self):
        """Initialize conversation store based on config."""
        if settings.memory_backend == "sqlite":
            from app.core.memory.sqlite_store import SQLiteConversationStore
            return SQLiteConversationStore(
                db_path=settings.sqlite_path,
                max_turns=settings.memory_max_turns,
                ttl_seconds=settings.memory_ttl_seconds,
            )
        return ConversationStore(
            max_turns=settings.memory_max_turns,
            ttl_seconds=settings.memory_ttl_seconds,
        )

    async def initialize(self, config_path: str = "omnibot.json"):
        """Load MCP servers and register built-in tools."""
        if self._initialized:
            return

        # Initialize SQLite store if needed
        if hasattr(self.conversations, 'initialize'):
            await self.conversations.initialize()

        # Load MCP tools from config
        await self.registry.load_from_config(config_path)

        # Register RAG as a built-in tool
        self.registry.register_builtin(
            name="knowledge_search",
            description="Search the local knowledge base (RAG). Use this when the user asks about uploaded documents or company-specific information.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                },
                "required": ["query"],
            },
            handler=self._rag_search,
        )

        tool_count = len(self.registry.tool_names)
        logger.info(f"AgentEngine initialized with {tool_count} tools: {self.registry.tool_names}")
        self._initialized = True

    async def _rag_search(self, query: str) -> str:
        """Built-in RAG search tool handler."""
        context, sources = await self.rag.retrieve(query)
        if not context:
            return "No relevant documents found in the knowledge base."
        source_str = ", ".join(sources) if sources else "unknown"
        return f"Sources: {source_str}\n\n{context}"

    async def _get_history(self, session_id: str | None) -> tuple[str, list[dict]]:
        """Get or create session + load history. Works with both sync and async stores."""
        if hasattr(self.conversations, 'initialize'):
            # async SQLite store
            sid = await self.conversations.get_or_create(session_id)
            history = await self.conversations.get_history(sid)
        else:
            sid = self.conversations.get_or_create(session_id)
            history = self.conversations.get_history(sid)
        return sid, history

    async def _save_message(self, session_id: str, role: str, content: str):
        """Save message to store. Works with both sync and async stores."""
        if hasattr(self.conversations, 'initialize'):
            await self.conversations.add_message(session_id, role, content)
        else:
            self.conversations.add_message(session_id, role, content)

    async def chat(self, message: BotMessage) -> BotResponse:
        """Process a chat message through the agent loop."""
        if not self._initialized:
            await self.initialize()

        session_id, history = await self._get_history(message.session_id)
        await self._save_message(session_id, "user", message.text)

        agent = AgentLoop(
            llm=self.llm,
            registry=self.registry,
            system_prompt=self.system_prompt,
            max_iterations=settings.max_agent_iterations,
        )

        result: AgentResult = await agent.run(
            message.text, conversation=history if history else None
        )

        await self._save_message(session_id, "assistant", result.response)

        sources = []
        for step in result.steps:
            for tc in step.tool_calls:
                if tc.tool_name == "knowledge_search" and "Sources:" in tc.result:
                    line = tc.result.split("\n")[0]
                    sources.extend(s.strip() for s in line.replace("Sources:", "").split(","))

        return BotResponse(
            text=result.response,
            sources=sources if sources else None,
            session_id=session_id,
            tool_calls_count=result.total_tool_calls,
            agent_steps=len(result.steps),
        )

    async def chat_stream(
        self, message: BotMessage,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming chat — yields SSE events, saves to memory on completion."""
        if not self._initialized:
            await self.initialize()

        session_id, history = await self._get_history(message.session_id)
        await self._save_message(session_id, "user", message.text)

        agent = AgentLoop(
            llm=self.llm,
            registry=self.registry,
            system_prompt=self.system_prompt,
            max_iterations=settings.max_agent_iterations,
        )

        final_response = ""
        async for event in agent.run_stream(
            message.text, conversation=history if history else None
        ):
            if event.get("event", event.get("type")) == "done":
                final_response = event.get("response", "")
            yield event

        # Save assistant response after stream completes
        if final_response:
            await self._save_message(session_id, "assistant", final_response)

    async def run_agent(
        self,
        message: str,
        system_prompt: str | None = None,
        conversation: list[dict] | None = None,
        session_id: str | None = None,
        max_iterations: int | None = None,
    ) -> AgentResult:
        """Run the agent loop directly (for advanced usage / API)."""
        if not self._initialized:
            await self.initialize()

        effective_conversation = conversation
        resolved_session_id = None
        if session_id and conversation is None:
            resolved_session_id, effective_conversation = await self._get_history(session_id)
            effective_conversation = effective_conversation or None
            await self._save_message(resolved_session_id, "user", message)

        agent = AgentLoop(
            llm=self.llm,
            registry=self.registry,
            system_prompt=system_prompt or self.system_prompt,
            max_iterations=max_iterations or settings.max_agent_iterations,
        )

        result = await agent.run(message, conversation=effective_conversation)

        if resolved_session_id:
            await self._save_message(resolved_session_id, "assistant", result.response)

        return result

    async def shutdown(self):
        """Clean shutdown of all MCP servers."""
        await self.registry.shutdown()
        if hasattr(self.conversations, 'close'):
            await self.conversations.close()
        self._initialized = False


# Global engine instance
engine = AgentEngine()
