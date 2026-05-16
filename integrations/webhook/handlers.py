import asyncio
import os
from datetime import datetime
from typing import Optional

from ai.runs.integration_handler import handle_integration_message
from ai.runs.one_action import get_user_facing_error_message
from ai.runs.session_manager import Platform, SessionSource, SessionStore
from ai.runs.stop_registry import request_stop
from ai.tools.manage_api_key import clear_api_key, set_api_key
from ai.utils.logger import log_conversation

from integrations.webhook.utils import (
    check_credentials_by_token,
    clear_user_busy,
    is_user_busy,
    send_webchat_message,
    set_user_busy,
)

session_store = SessionStore()

def build_webchat_session_source(user_id: str) -> SessionSource:
    """Build the session source for the current WebChat conversation."""
    return SessionSource(
        platform=Platform.WEBCHAT,
        chat_id=user_id,
        user_id=user_id,
        chat_type="dm",
    )

def get_webchat_stop_key(user_id: str) -> str:
    """Return a stable conversation key for stop/cancel lookup."""
    return session_store._generate_session_key(build_webchat_session_source(user_id))

def get_webchat_session_id(user_id: str) -> str:
    """Get or create session ID for WebChat conversation."""
    return session_store.get_or_create_session_id(build_webchat_session_source(user_id))

def _extract_command(message_text: str) -> Optional[str]:
    cleaned = (message_text or "").strip()
    if not cleaned.startswith("/"):
        return None
    return cleaned.split()[0].lower()

class WebChatProgressBridge:
    """Collapse intermediate agent updates into WebChat messages."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.messages: list[str] = []

    async def push(self, msg: str) -> None:
        cleaned = (msg or "").strip()
        if not cleaned:
            return

        self.messages.append(cleaned)
        # Send each intermediate message back to the web chat
        await send_webchat_message(self.user_id, cleaned)

    async def finalize(self) -> None:
        if not self.messages:
            return


async def handle_webchat_message(user_id: str, message_text: str, token: str):
    """
    Handle messages from the web chat webhook.
    """
    command_text = _extract_command(message_text)
    
    if is_user_busy(user_id) and command_text != "/stop":
        try:
            await send_webchat_message(user_id, "wait I'm processing your last message 👀")
        except Exception:
            pass
        return

    set_user_busy(user_id)
    
    try:
        if command_text == "/stop":
            is_valid, credentials, error, user_info = await check_credentials_by_token(token)
            if not is_valid:
                clear_user_busy(user_id)
                return

            stopped = request_stop(get_webchat_stop_key(user_id))
            clear_user_busy(user_id)

            if stopped:
                await send_webchat_message(user_id, "Agent has been stopped.")
            else:
                await send_webchat_message(user_id, "There is no active run to stop.")
            return

        if command_text in ["/new", "/reset"]:
            is_valid, credentials, error, user_info = await check_credentials_by_token(token)
            if not is_valid:
                clear_user_busy(user_id)
                return

            results = credentials.get("results", [])
            if results:
                user_data = results[0]
                keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
                crm_api_key = keys.get("crm_api_key")
                if crm_api_key:
                    set_api_key(crm_api_key)

            session_store.reset_session(build_webchat_session_source(user_id))
            await send_webchat_message(
                user_id, 
                "✨ Session reset! Starting fresh.\n\n"
                "Previous chat history cleared. How can I help you with the CRM today?"
            )
            clear_api_key()
            clear_user_busy(user_id)
            return

        # Main message handling
        is_valid, credentials, error, user_info = await check_credentials_by_token(token)
        if not is_valid:
            if error == "credit_limit":
                await send_webchat_message(user_id, "You've used all your credits for this month. 🚀")
            else:
                await send_webchat_message(user_id, f"Invalid credentials: {error}")
            clear_user_busy(user_id)
            return

        # Set API key from credentials
        results = credentials.get("results", [])
        if results:
            user_data = results[0]
            keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
            crm_api_key = keys.get("crm_api_key")
            if crm_api_key:
                set_api_key(crm_api_key)

        started_at = datetime.utcnow()
        log_conversation({
            "channel": "webchat",
            "message_type": "txt",
            "user": user_info,
            "inbound": {"user_msg": message_text[:1000]},
            "timing": {"started_at": started_at.isoformat() + "Z"},
        })

        progress_bridge = WebChatProgressBridge(user_id)

        async def send_message_callback(msg: str):
            await progress_bridge.push(msg)

        session_id = get_webchat_session_id(user_id)
        
        try:
            result = await handle_integration_message(
                message_text,
                credentials,
                message_callback=send_message_callback,
                session_id=session_id,
                stop_key=get_webchat_stop_key(user_id),
            )
        except asyncio.CancelledError:
            return

        await progress_bridge.finalize()

        if result.get("status") == "context_limit":
            await send_webchat_message(user_id, result["message"])
            session_store.reset_session(build_webchat_session_source(user_id))
            await send_webchat_message(
                user_id, 
                "✨ Session reset! Starting fresh.\n\n"
                "Previous chat history cleared. How can I help you with the CRM today?"
            )
            clear_api_key()
            clear_user_busy(user_id)
            return

        if result.get("status") == "stopped":
            return

        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()
        log_conversation({
            "channel": "webchat",
            "message_type": "txt",
            "user": user_info,
            "outbound": {
                "messages": [msg[:500] for msg in progress_bridge.messages],
                "message_count": len(progress_bridge.messages),
            },
            "timing": {
                "started_at": started_at.isoformat() + "Z",
                "completed_at": completed_at.isoformat() + "Z",
                "duration_seconds": round(duration_seconds, 2),
            },
        })

    except Exception as e:
        print(f"WebChat handler error for user {user_id}: {e}")
        try:
            await send_webchat_message(user_id, get_user_facing_error_message(e))
        except Exception:
            pass
    finally:
        clear_api_key()
        clear_user_busy(user_id)
