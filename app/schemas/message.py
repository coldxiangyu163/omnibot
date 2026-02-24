from pydantic import BaseModel
from datetime import datetime


class BotMessage(BaseModel):
    """Unified message format across all channels."""
    channel: str = "web"
    sender_id: str = "anonymous"
    text: str
    session_id: str | None = None
    timestamp: datetime | None = None
    metadata: dict | None = None


class BotResponse(BaseModel):
    text: str
    sources: list[str] | None = None
    session_id: str | None = None
