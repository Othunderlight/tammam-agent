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
from ai.workflows.utils.msg_stt import transcribe_audio
from neonize.aioze.client import NewAClient
from neonize.aioze.events import MessageEv
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import AudioMessage
from neonize.utils import get_message_type

from integrations.whatsapp.utils import (
    check_credentials,
    clear_user_busy,
    edit_text,
    is_user_busy,
    reply_text,
    send_text,
    set_user_busy,
    start_typing_indicator,
    stop_typing_indicator,
)

VOICE_STT_MODEL = os.getenv("VOICE_STT_MODEL", "gemini-2.5-flash")

session_store = SessionStore()


def _safe_text(event: MessageEv) -> str:
    """Extract text from a WhatsApp message."""
    message = event.Message
    if message.conversation:
        return message.conversation.strip()

    extended = getattr(message, "extendedTextMessage", None)
    if extended and extended.text:
        return extended.text.strip()

    return ""


def _get_sender_id(event: MessageEv) -> str:
    sender = getattr(event.Info.MessageSource, "Sender", None)
    if sender and sender.User:
        return str(sender.User)
    return ""


def _get_chat_id(event: MessageEv) -> str:
    chat = getattr(event.Info.MessageSource, "Chat", None)
    if chat and getattr(chat, "User", None):
        return str(chat.User)
    return _get_sender_id(event)


def _get_chat_name(event: MessageEv) -> Optional[str]:
    chat = getattr(event.Info.MessageSource, "Chat", None)
    if chat and getattr(chat, "Server", None):
        return str(chat.Server)
    return None


def _is_voice_message(event: MessageEv) -> bool:
    msg_type = get_message_type(event.Message)
    return isinstance(msg_type, AudioMessage)


def build_whatsapp_session_source(event: MessageEv) -> SessionSource:
    """Build the session source for the current WhatsApp conversation."""
    chat_type = "group" if getattr(event.Info.MessageSource, "IsGroup", False) else "dm"
    return SessionSource(
        platform=Platform.WHATSAPP,
        chat_id=_get_chat_id(event),
        chat_name=_get_chat_name(event),
        chat_type=chat_type,
        user_id=_get_sender_id(event) or None,
        user_name=_get_sender_id(event) or None,
    )


def get_whatsapp_stop_key(event: MessageEv) -> str:
    """Return a stable conversation key for stop/cancel lookup."""
    return session_store._generate_session_key(build_whatsapp_session_source(event))


def get_whatsapp_session_id(event: MessageEv) -> str:
    """Get or create session ID for WhatsApp conversation."""
    return session_store.get_or_create_session_id(build_whatsapp_session_source(event))


def _extract_command(message_text: str) -> Optional[str]:
    cleaned = (message_text or "").strip()
    if not cleaned.startswith("/"):
        return None
    return cleaned.split()[0].lower()


def _get_crm_api_key(credentials: dict) -> Optional[str]:
    results = credentials.get("results", [])
    if not results:
        return None

    user_data = results[0]
    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
    return keys.get("crm_api_key")


class WhatsAppProgressBridge:
    """Collapse intermediate agent updates into one editable WhatsApp message."""

    def __init__(self, client: NewAClient, chat_jid):
        self._client = client
        self._chat_jid = chat_jid
        self._status_id: Optional[str] = None
        self._last_status_text: Optional[str] = None
        self.messages: list[str] = []

    async def push(self, msg: str) -> None:
        cleaned = (msg or "").strip()
        if not cleaned:
            return

        self.messages.append(cleaned)
        if self._status_id is None:
            sent = await send_text(self._client, self._chat_jid, cleaned)
            self._status_id = sent.ID
            self._last_status_text = cleaned
            return

        if cleaned == self._last_status_text:
            return

        await edit_text(self._client, self._chat_jid, self._status_id, cleaned)
        self._last_status_text = cleaned

    async def finalize(self) -> None:
        if not self.messages:
            return


async def _handle_context_limit(
    client: NewAClient,
    event: MessageEv,
    credentials: dict,
    message: str,
) -> None:
    await reply_text(client, event, message)

    crm_api_key = _get_crm_api_key(credentials)
    if crm_api_key:
        set_api_key(crm_api_key)

    session_store.reset_session(build_whatsapp_session_source(event))
    await reply_text(
        client,
        event,
        "✨ Session reset! Starting fresh.\n\n"
        "Previous chat history cleared. How can I help you with the CRM today?",
    )
    clear_api_key()


async def handle_whatsapp_message(client: NewAClient, event: MessageEv):
    sender_id = _get_sender_id(event)
    if not sender_id or event.Info.MessageSource.IsFromMe:
        return

    message_text = _safe_text(event)
    is_voice = _is_voice_message(event)
    if not message_text and not is_voice:
        return

    command_text = _extract_command(message_text)
    if is_user_busy(sender_id) and command_text != "/stop":
        try:
            await reply_text(client, event, "wait I'm processing your last message 👀")
        except Exception:
            pass
        return

    set_user_busy(sender_id)
    chat_jid = event.Info.MessageSource.Chat
    chat_id = _get_chat_id(event)
    typing_task: Optional[asyncio.Task] = None

    try:
        if command_text == "/stop":
            is_valid, credentials, _, user_info = await check_credentials(
                client, event, sender_id, chat_id
            )
            if not is_valid:
                clear_user_busy(sender_id)
                return

            del credentials, user_info
            stopped = request_stop(get_whatsapp_stop_key(event))
            clear_user_busy(sender_id)

            if stopped:
                await reply_text(client, event, "Agent has been stopped.")
            else:
                await reply_text(client, event, "There is no active run to stop.")
            return

        if command_text == "/help":
            is_valid, credentials, _, user_info = await check_credentials(
                client, event, sender_id, chat_id
            )
            if not is_valid:
                clear_user_busy(sender_id)
                return

            del credentials, user_info
            await reply_text(
                client,
                event,
                "🤖 Commands:\n\n"
                "/new - Create new session, reset the context\n"
                "/reset - Same as /new\n"
                "/stop - Stop the active run\n"
                "/help - Show this menu",
            )
            clear_user_busy(sender_id)
            return

        if command_text == "/start":
            is_valid, credentials, _, user_info = await check_credentials(
                client, event, sender_id, chat_id
            )
            if not is_valid:
                clear_user_busy(sender_id)
                return

            del credentials, user_info
            typing_task = start_typing_indicator(client, chat_jid)
            try:
                await reply_text(client, event, "Hi & Welcome 🤗")
                await asyncio.sleep(2)
                await reply_text(
                    client,
                    event,
                    "I'm TMM تمّ - privacy-first agent with conversation memory.\n\n"
                    "I remember our conversation history, so you can reference previous messages!\n\n"
                    "support: @Omar_Gatara",
                )
                await asyncio.sleep(2)
                await reply_text(
                    client,
                    event,
                    "How can I work with you on the CRM today?",
                )
            finally:
                await stop_typing_indicator(client, chat_jid, typing_task)
                clear_user_busy(sender_id)
            return

        if command_text in ["/new", "/reset"]:
            is_valid, credentials, _, user_info = await check_credentials(
                client, event, sender_id, chat_id
            )
            if not is_valid:
                clear_user_busy(sender_id)
                return

            del user_info
            crm_api_key = _get_crm_api_key(credentials)
            if not crm_api_key:
                await reply_text(client, event, "❌ CRM API key not found.")
                clear_user_busy(sender_id)
                return

            set_api_key(crm_api_key)
            session_store.reset_session(build_whatsapp_session_source(event))
            await reply_text(
                client,
                event,
                "✨ Session reset! Starting fresh.\n\n"
                "Previous chat history cleared. How can I help you with the CRM today?",
            )
            clear_api_key()
            clear_user_busy(sender_id)
            return

        if command_text:
            is_valid, credentials, _, user_info = await check_credentials(
                client, event, sender_id, chat_id
            )
            if not is_valid:
                clear_user_busy(sender_id)
                return

            del credentials, user_info
            await reply_text(
                client,
                event,
                "❓ Unknown command. Type /help to see what I can do.",
            )
            clear_user_busy(sender_id)
            return

        is_valid, credentials, _, user_info = await check_credentials(
            client, event, sender_id, chat_id
        )
        if not is_valid:
            clear_user_busy(sender_id)
            return

        crm_api_key = _get_crm_api_key(credentials)
        if crm_api_key:
            set_api_key(crm_api_key)

        started_at = datetime.utcnow()
        log_payload = {
            "channel": "whatsapp",
            "message_type": "voice" if is_voice else "txt",
            "user": user_info,
            "timing": {"started_at": started_at.isoformat() + "Z"},
        }

        if is_voice:
            log_payload["inbound"] = {"voice_received": True}
            await reply_text(client, event, "listening...")
        else:
            log_payload["inbound"] = {"user_msg": message_text[:1000]}
            await reply_text(client, event, "Ok, thinking...")

        log_conversation(log_payload)

        progress_bridge = WhatsAppProgressBridge(client, chat_jid)
        typing_task = start_typing_indicator(client, chat_jid)

        async def send_message_callback(msg: str):
            await progress_bridge.push(msg)

        session_id = get_whatsapp_session_id(event)

        if is_voice:
            try:
                audio_bytes = await client.download_any(event.Message)
                mime_type = getattr(
                    get_message_type(event.Message), "mimetype", "audio/ogg"
                )
                transcribed_text = await transcribe_audio(
                    audio_data=audio_bytes,
                    mime_type=mime_type,
                    model=VOICE_STT_MODEL,
                )
                if not transcribed_text:
                    await reply_text(
                        client,
                        event,
                        "Sorry, couldn't transcribe the voice message. Please try again or send a text.",
                    )
                    return

                message_text = transcribed_text
                log_conversation(
                    {
                        "channel": "whatsapp",
                        "message_type": "voice",
                        "user": user_info,
                        "inbound": {"transcribed_text": transcribed_text[:1000]},
                    }
                )
            except Exception as e:
                print(f"WhatsApp voice transcription error for user {sender_id}: {e}")
                await reply_text(
                    client,
                    event,
                    "Sorry, couldn't transcribe the voice message. Please try again or send a text.",
                )
                return

        try:
            result = await handle_integration_message(
                message_text,
                credentials,
                message_callback=send_message_callback,
                session_id=session_id,
                stop_key=get_whatsapp_stop_key(event),
            )
        except asyncio.CancelledError:
            return

        await progress_bridge.finalize()

        if result.get("status") == "context_limit":
            await _handle_context_limit(client, event, credentials, result["message"])
            return

        if result.get("status") == "stopped":
            return

        outbound_messages = progress_bridge.messages
        if not outbound_messages:
            await reply_text(
                client,
                event,
                "I didn't get a usable response from the agent. Please try again in a moment.",
            )

        completed_at = datetime.utcnow()
        duration_seconds = (completed_at - started_at).total_seconds()
        log_conversation(
            {
                "channel": "whatsapp",
                "message_type": "voice" if is_voice else "txt",
                "user": user_info,
                "outbound": {
                    "messages": [msg[:500] for msg in outbound_messages],
                    "message_count": len(outbound_messages),
                },
                "timing": {
                    "started_at": started_at.isoformat() + "Z",
                    "completed_at": completed_at.isoformat() + "Z",
                    "duration_seconds": round(duration_seconds, 2),
                },
            }
        )
    except Exception as e:
        print(f"WhatsApp handler error for user {sender_id}: {e}")
        try:
            await reply_text(client, event, get_user_facing_error_message(e))
        except Exception:
            pass
    finally:
        if typing_task:
            await stop_typing_indicator(client, chat_jid, typing_task)
        clear_api_key()
        clear_user_busy(sender_id)
