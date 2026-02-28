"""Web channel — WebSocket chat with streaming agent support."""
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

            # Use streaming by default
            async for event in engine.chat_stream(msg):
                event_type = event.get("event", "unknown")
                if event_type == "content_delta":
                    await ws.send_json({"type": "delta", "delta": event["delta"]})
                elif event_type == "tool_start":
                    await ws.send_json({
                        "type": "tool_start",
                        "tool": event["tool"],
                        "arguments": event.get("arguments", {}),
                    })
                elif event_type == "tool_result":
                    await ws.send_json({
                        "type": "tool_result",
                        "tool": event["tool"],
                        "result": event.get("result", ""),
                        "duration_ms": event.get("duration_ms", 0),
                    })
                elif event_type == "done":
                    await ws.send_json({
                        "type": "message",
                        "text": event.get("response", ""),
                        "total_tool_calls": event.get("total_tool_calls", 0),
                        "duration_ms": event.get("duration_ms", 0),
                    })
    except WebSocketDisconnect:
        pass
