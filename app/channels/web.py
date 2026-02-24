"""Web channel — WebSocket chat with agent support."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import uuid
import json
from app.schemas.message import BotMessage
from app.core.engine import engine

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())
    await ws.send_json({"type": "session", "session_id": session_id})
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            msg = BotMessage(
                channel="web", text=payload.get("text", ""),
                session_id=session_id,
            )
            response = await engine.chat(msg)
            await ws.send_json({
                "type": "message",
                "text": response.text,
                "sources": response.sources,
                "tool_calls_count": response.tool_calls_count,
                "agent_steps": response.agent_steps,
            })
    except WebSocketDisconnect:
        pass
