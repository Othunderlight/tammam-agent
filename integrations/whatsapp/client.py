import asyncio
import os
from contextlib import suppress

from auth import verify_token
from fastapi import Depends, FastAPI, HTTPException
from neonize.aioze.client import NewAClient
from neonize.aioze.events import ConnectedEv, MessageEv
from neonize.utils import build_jid
from pydantic import BaseModel

from integrations.send_message_auth import authorize_whatsapp_send_message
from integrations.whatsapp.utils import send_text

WHATSAPP_SESSION_DB = os.getenv("WHATSAPP_SESSION_DB", "/app/neonize.db")

whatsapp_client = NewAClient(WHATSAPP_SESSION_DB)
_connection_task = None


class SendWhatsAppMessageRequest(BaseModel):
    chat_id: str
    phone_number: str
    message: str


@whatsapp_client.event(ConnectedEv)
async def on_connected(client: NewAClient, event: ConnectedEv):
    del event
    del client


@whatsapp_client.event(MessageEv)
async def on_message(client: NewAClient, event: MessageEv):
    from integrations.whatsapp.handlers import handle_whatsapp_message

    asyncio.create_task(handle_whatsapp_message(client, event))


async def init_whatsapp() -> None:
    """Start the WhatsApp client in the background."""
    global _connection_task

    if _connection_task and not _connection_task.done():
        return

    print("🚀 Starting WhatsApp client...")
    _connection_task = asyncio.create_task(whatsapp_client.connect())


async def shutdown_whatsapp() -> None:
    """Disconnect the WhatsApp client cleanly."""
    global _connection_task

    try:
        await whatsapp_client.disconnect()
    except Exception:
        pass

    if _connection_task:
        _connection_task.cancel()
        with suppress(asyncio.CancelledError):
            await _connection_task
        _connection_task = None


def register_whatsapp_routes(app: FastAPI) -> None:
    """Register WhatsApp operational endpoints."""

    @app.get("/webhooks/whatsapp/health")
    async def whatsapp_health():
        me = whatsapp_client.me
        return {
            "status": "healthy" if whatsapp_client.connected else "starting",
            "connected": whatsapp_client.connected,
            "device_id": me.JID.User if me else None,
            "session_db": WHATSAPP_SESSION_DB,
        }

    @app.post("/whatsapp/send-message")
    async def send_whatsapp_message(
        request: SendWhatsAppMessageRequest,
        user_data: dict = Depends(verify_token),
    ):
        """Send a WhatsApp message to a user by their WhatsApp chat ID."""
        if not whatsapp_client.connected:
            return {"status": "error", "message": "WhatsApp client not initialized"}

        try:
            await authorize_whatsapp_send_message(request.phone_number, user_data)
            chat_jid = build_jid(request.phone_number)
            await send_text(whatsapp_client, chat_jid, request.message)
            return {"status": "success", "message": "Message sent"}
        except HTTPException:
            raise
        except Exception as e:
            return {"status": "error", "message": str(e)}
