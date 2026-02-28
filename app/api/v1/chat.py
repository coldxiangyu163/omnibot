"""Chat API — supports both regular and streaming responses."""
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.schemas.message import BotMessage, BotResponse
from app.core.engine import engine

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=BotResponse)
async def chat(message: BotMessage):
    return await engine.chat(message)


@router.post("/chat/stream")
async def chat_stream(message: BotMessage):
    """
    Streaming chat endpoint. Returns Server-Sent Events (SSE).
    Conversation memory is automatically managed via session_id.

    Event types:
        step_start    — {"step": 1}
        content_delta — {"delta": "partial text..."}
        tool_start    — {"tool": "name", "arguments": {...}}
        tool_result   — {"tool": "name", "result": "...", "duration_ms": 42}
        done          — {"response": "full text", "total_tool_calls": N}
    """
    async def event_generator():
        async for event in engine.chat_stream(message):
            event_type = event.get("event", "unknown")
            data = json.dumps(event, ensure_ascii=False)
            yield f"event: {event_type}\ndata: {data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
