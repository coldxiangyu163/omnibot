from app.core.llm.base import LLMProvider
from app.core.llm.openai_provider import OpenAIProvider
from app.core.llm.anthropic_provider import AnthropicProvider
from app.core.rag.pipeline import RAGPipeline
from app.schemas.message import BotMessage, BotResponse
from app.config import settings


class BotEngine:
    """Core bot orchestrator — routes messages through RAG + LLM."""

    def __init__(self):
        self.llm = self._init_llm()
        self.rag = RAGPipeline()
        self.system_prompt = (
            "You are OmniBot, a helpful AI assistant. "
            "Answer questions based on the provided context. "
            "If the context doesn't contain relevant information, "
            "say so honestly and answer from general knowledge."
        )

    def _init_llm(self) -> LLMProvider:
        if settings.llm_provider == "anthropic":
            return AnthropicProvider()
        return OpenAIProvider()

    async def chat(self, message: BotMessage) -> BotResponse:
        context, sources = await self.rag.retrieve(message.text)
        prompt = message.text
        if context:
            prompt = f"Context:\n{context}\n\nQuestion: {message.text}"
        response_text = await self.llm.generate(
            prompt=prompt, system=self.system_prompt,
            session_id=message.session_id,
        )
        return BotResponse(
            text=response_text,
            sources=sources if sources else None,
            session_id=message.session_id,
        )


engine = BotEngine()
