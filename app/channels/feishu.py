"""
Feishu (Lark) channel — receive messages via event callback, reply via API.

Setup:
1. Create a Feishu bot at https://open.feishu.cn
2. Enable "Bot" capability, set event callback URL to: https://your-host/feishu/event
3. Set FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_VERIFICATION_TOKEN in .env
4. Subscribe to "im.message.receive_v1" event
"""
from __future__ import annotations

import hashlib
import json
import time
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.message import BotMessage
from app.core.engine import engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feishu", tags=["feishu"])

# Token cache
_token_cache: dict[str, Any] = {"token": "", "expires_at": 0}
# Dedup: message_id -> timestamp
_seen_messages: dict[str, float] = {}
_DEDUP_TTL = 300  # 5 min


async def _get_tenant_access_token() -> str:
    """Get or refresh tenant_access_token."""
    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            json={
                "app_id": settings.feishu_app_id,
                "app_secret": settings.feishu_app_secret,
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"Failed to get feishu token: {data}")
            raise RuntimeError(f"Feishu token error: {data.get('msg')}")

        _token_cache["token"] = data["tenant_access_token"]
        _token_cache["expires_at"] = now + data.get("expire", 7200)
        return _token_cache["token"]


async def _reply_message(message_id: str, text: str):
    """Reply to a feishu message."""
    token = await _get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": json.dumps({"text": text}),
                "msg_type": "text",
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"Failed to reply: {data}")


async def _send_message(chat_id: str, text: str):
    """Send a message to a feishu chat."""
    token = await _get_tenant_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.feishu.cn/open-apis/im/v1/messages",
            headers={"Authorization": f"Bearer {token}"},
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": chat_id,
                "content": json.dumps({"text": text}),
                "msg_type": "text",
            },
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error(f"Failed to send: {data}")


def _dedup_check(message_id: str) -> bool:
    """Return True if this message was already seen (duplicate)."""
    now = time.time()
    # Cleanup old entries
    expired = [k for k, v in _seen_messages.items() if now - v > _DEDUP_TTL]
    for k in expired:
        del _seen_messages[k]

    if message_id in _seen_messages:
        return True
    _seen_messages[message_id] = now
    return False


def _extract_text(event: dict) -> str | None:
    """Extract plain text from feishu message event."""
    msg = event.get("message", {})
    msg_type = msg.get("message_type")
    if msg_type != "text":
        return None
    try:
        content = json.loads(msg.get("content", "{}"))
        return content.get("text", "").strip()
    except (json.JSONDecodeError, AttributeError):
        return None


@router.post("/event")
async def feishu_event(request: Request):
    """
    Feishu event callback endpoint.
    Handles: URL verification, message events.
    """
    body = await request.json()

    # URL verification challenge
    if body.get("type") == "url_verification":
        return JSONResponse({"challenge": body.get("challenge", "")})

    # Schema v2 event
    header = body.get("header", {})
    event = body.get("event", {})

    # Verify token
    if settings.feishu_verification_token:
        token = header.get("token", "")
        if token != settings.feishu_verification_token:
            logger.warning("Invalid verification token")
            return JSONResponse({"code": 403, "msg": "invalid token"}, status_code=403)

    event_type = header.get("event_type", "")
    if event_type != "im.message.receive_v1":
        return JSONResponse({"code": 0})

    # Extract message info
    message = event.get("message", {})
    message_id = message.get("message_id", "")
    chat_id = message.get("chat_id", "")
    sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")

    # Dedup (feishu may retry)
    if _dedup_check(message_id):
        return JSONResponse({"code": 0})

    # Extract text
    text = _extract_text(event)
    if not text:
        return JSONResponse({"code": 0})

    # Ignore bot's own messages
    if event.get("sender", {}).get("sender_type") == "app":
        return JSONResponse({"code": 0})

    logger.info(f"Feishu message from {sender_id} in {chat_id}: {text[:100]}")

    # Use chat_id as session_id for multi-turn
    msg = BotMessage(
        channel="feishu",
        sender_id=sender_id,
        text=text,
        session_id=chat_id,
        metadata={"message_id": message_id, "chat_id": chat_id},
    )

    # Respond async — reply immediately with 200, process in background
    import asyncio
    asyncio.create_task(_process_and_reply(msg, message_id, chat_id))

    return JSONResponse({"code": 0})


async def _process_and_reply(msg: BotMessage, message_id: str, chat_id: str):
    """Process message and reply via feishu API."""
    try:
        response = await engine.chat(msg)
        if response.text:
            await _reply_message(message_id, response.text)
    except Exception:
        logger.exception("Error processing feishu message")
        try:
            await _send_message(chat_id, "Sorry, I encountered an error processing your message.")
        except Exception:
            logger.exception("Failed to send error message")
