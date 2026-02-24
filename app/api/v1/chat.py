"""Chat API — backward compatible."""
from fastapi import APIRouter
from app.schemas.message import BotMessage, BotResponse
from app.core.engine import engine

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=BotResponse)
async def chat(message: BotMessage):
    return await engine.chat(message)
