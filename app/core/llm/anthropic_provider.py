from anthropic import AsyncAnthropic
from app.core.llm.base import LLMProvider
from app.config import settings


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    async def generate(self, prompt: str, system: str = "", session_id: str | None = None) -> str:
        response = await self.client.messages.create(
            model=self.model, max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
