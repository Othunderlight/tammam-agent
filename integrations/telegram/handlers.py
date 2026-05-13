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
from telegram import Bot, Message, Update
from telegram.constants import ParseMode

from integrations.telegram.utils import (
    check_credentials,
    clear_user_busy,
    forward_to_n8n,
    get_telegram_file_path,
    is_duplicate_update,
    is_user_busy,
    md_to_telegram_html,
    set_user_busy,
    start_typing_indicator,
    stop_typing_indicator,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ERROR_CHAT_ID = os.getenv("TELEGRAM_ERROR_CHAT_ID")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
VOICE_STT_MODEL = os.getenv("VOICE_STT_MODEL", "gemini-2.5-flash")

# Initialize session store
session_store = SessionStore()


def build_telegram_session_source(update: Update) -> SessionSource:
    """Build the session source for the current Telegram conversation."""
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if chat.type in (chat.type.GROUP, chat.type.SUPERGROUP):
        chat_type = "group"
    elif chat.type == chat.type.CHANNEL:
        chat_type = "channel"
    else:
        chat_type = "dm"

    return SessionSource(
        platform=Platform.TELEGRAM,
        chat_id=str(chat.id),
        chat_name=chat.title or getattr(chat, "full_name", None),
        chat_type=chat_type,
        user_id=str(user.id) if user else None,
        user_name=user.full_name if user else None,
        thread_id=str(message.message_thread_id)
        if message and message.message_thread_id
        else None,
    )


def get_telegram_stop_key(update: Update) -> str:
    """Return a stable conversation key for stop/cancel lookup."""
    return session_store._generate_session_key(build_telegram_session_source(update))


def get_telegram_session_id(update, user_info) -> str:
    """Get or create session ID for Telegram conversation."""
    del user_info
    return session_store.get_or_create_session_id(build_telegram_session_source(update))


def _normalize_outbound_message(msg: str) -> Optional[str]:
    cleaned = (msg or "").strip()
    return cleaned or None


class TelegramProgressBridge:
    """Collapse intermediate agent updates into one editable Telegram message."""

    def __init__(self, source_message: Message):
        self._source_message = source_message
        self._status_message: Optional[Message] = None
        self._last_status_html: Optional[str] = None
        self.messages: list[str] = []

    async def push(self, msg: str) -> None:
        cleaned = _normalize_outbound_message(msg)
        if not cleaned:
            return

        self.messages.append(cleaned)
        html_answer = md_to_telegram_html(cleaned).strip()
        if not html_answer:
            return

        if self._status_message is None:
            self._status_message = await self._source_message.reply_text(
                html_answer,
                parse_mode=ParseMode.HTML,
            )
            self._last_status_html = html_answer
            return

        if html_answer == self._last_status_html:
            return

        try:
            await self._status_message.edit_text(
                html_answer,
                parse_mode=ParseMode.HTML,
            )
            self._last_status_html = html_answer
        except Exception as e:
            if "message is not modified" in str(e).lower():
                return
            raise

    async def finalize(self) -> None:
        if not self.messages:
            return

        if len(self.messages) == 1:
            return


def _extract_bot_command(update: Update) -> Optional[str]:
    message = update.message
    if not message or not message.text or not message.entities:
        return None

    for entity in message.entities:
        if entity.type != "bot_command":
            continue
        return message.text[entity.offset : entity.offset + entity.length]

    return None


async def _notify_debug_issue(title: str, details: str) -> None:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_ERROR_CHAT_ID):
        print(f"[debug] {title}: {details}")
        return

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_ERROR_CHAT_ID,
            text=f"⚠️ {title}\n{details}",
        )
    except Exception as debug_error:
        print(
            f"Failed to send debug notice to group {TELEGRAM_ERROR_CHAT_ID}: {debug_error}"
        )


async def handle_telegram_message(update: Update):
    try:
        if is_duplicate_update(update):
            return

        user_name = update.effective_user.first_name or "User"
        user_id = update.effective_user.id
        command_text = _extract_bot_command(update)

        if is_user_busy(user_id) and command_text != "/stop":
            try:
                await update.message.reply_text(
                    "wait I'm processing your last message 👀"
                )
            except Exception:
                pass  # Non-critical: if we can't send "please wait", just skip it
            return
        # Mark user as busy immediately after checking
        set_user_busy(user_id)
        chat_id = update.effective_chat.id
        typing_task: Optional[asyncio.Task] = None

        # Handle different message types
        try:
            # Handle pinned messages
            if update.message and update.message.pinned_message:
                clear_user_busy(user_id)
                return

            # 1. HANDLE CALLBACK QUERIES (Buttons)
            if update.callback_query:
                await update.callback_query.answer()
                # Wrap in 'callback_query' so n8n "Magic Code" finds it
                payload = {
                    "callback_query": {
                        "id": update.callback_query.id,
                        "data": update.callback_query.data,
                        "from": {
                            "first_name": update.effective_user.first_name,
                            "last_name": update.effective_user.last_name or "",
                        },
                        "message": {
                            "chat": {"id": chat_id},
                            "message_id": update.callback_query.message.message_id,
                        },
                    }
                }
                await forward_to_n8n(payload)
                clear_user_busy(user_id)
                return

            # 2. HANDLE BOT COMMANDS (e.g. /start, /guide)
            if command_text:
                if command_text == "/stop":
                    is_valid, credentials, _, user_info = await check_credentials(
                        update
                    )
                    if not is_valid:
                        clear_user_busy(user_id)
                        return

                    del credentials, user_info
                    stopped = request_stop(get_telegram_stop_key(update))
                    clear_user_busy(user_id)

                    if stopped:
                        await update.message.reply_text("Agent has been stopped.")
                    else:
                        await update.message.reply_text(
                            "There is no active run to stop."
                        )
                    return

                if command_text == "/start":
                    is_valid, credentials, _, user_info = await check_credentials(
                        update
                    )
                    if not is_valid:
                        clear_user_busy(user_id)
                        return

                    typing_task = start_typing_indicator(update.get_bot(), chat_id)
                    try:
                        await update.message.reply_text(f"Hi & Welcome {user_name} 🤗")
                        await asyncio.sleep(2)

                        start_message = (
                            "I'm TMM تمّ - privacy-first agent with conversation memory.\n\n"
                            "I remember our conversation history, so you can reference previous messages!\n\n"
                            "support: @Omar_Gatara"
                        )
                        sent_msg = await update.message.reply_text(start_message)
                        await asyncio.sleep(2)
                        await sent_msg.pin()
                        await asyncio.sleep(3)
                        await update.message.reply_text(
                            "How can I work with you on the CRM today?"
                        )
                    finally:
                        await stop_typing_indicator(typing_task)
                        clear_user_busy(user_id)
                    return

                if command_text in ["/new", "/reset"]:
                    is_valid, credentials, _, user_info = await check_credentials(
                        update
                    )
                    if not is_valid:
                        clear_user_busy(user_id)
                        return

                    results = credentials.get("results", [])
                    if results:
                        user_data = results[0]
                        keys = {
                            k["name"]: k["value"] for k in user_data.get("keys", [])
                        }
                        crm_api_key = keys.get("crm_api_key")

                        if crm_api_key:
                            set_api_key(crm_api_key)
                        else:
                            await update.message.reply_text(
                                f"❌ CRM API key not found. Keys available: {list(keys.keys())}"
                            )
                            clear_user_busy(user_id)
                            return
                    else:
                        await update.message.reply_text(
                            "❌ Invalid credentials structure."
                        )
                        clear_user_busy(user_id)
                        return

                    source = SessionSource(
                        platform=Platform.TELEGRAM,
                        chat_id=str(chat_id),
                        chat_name=update.effective_chat.title
                        or getattr(update.effective_chat, "full_name", None),
                        chat_type="dm",
                        user_id=str(user_id) if update.effective_user else None,
                        user_name=update.effective_user.full_name
                        if update.effective_user
                        else None,
                        thread_id=str(update.effective_message.message_thread_id)
                        if update.effective_message
                        and update.effective_message.message_thread_id
                        else None,
                    )

                    session_store.reset_session(source)
                    await update.message.reply_text(
                        "✨ Session reset! Starting fresh.\n\n"
                        "Previous chat history cleared. How can I help you with the CRM today?"
                    )
                    clear_api_key()
                    clear_user_busy(user_id)
                    return

                if command_text == "/guide":
                    is_valid, credentials, _, user_info = await check_credentials(
                        update
                    )
                    if not is_valid:
                        clear_user_busy(user_id)
                        return

                    started_at = datetime.utcnow()
                    log_conversation(
                        {
                            "channel": "telegram",
                            "message_type": "command",
                            "user": user_info,
                            "inbound": {"command": command_text},
                            "timing": {"started_at": started_at.isoformat() + "Z"},
                        }
                    )

                    payload = {
                        "message": {
                            "text": command_text,
                            "chat": {"id": chat_id},
                            "from": {
                                "first_name": update.effective_user.first_name,
                                "last_name": update.effective_user.last_name or "",
                            },
                        }
                    }
                    await forward_to_n8n(payload)

                clear_user_busy(user_id)
                return

            # 3. PHOTO HANDLER
            if update.message and update.message.photo:
                is_valid, credentials, _, _ = await check_credentials(update)
                if not is_valid:
                    clear_user_busy(user_id)
                    return
                await update.message.reply_text("sending images is not supported")
                clear_user_busy(user_id)
                return

            # 4. VIDEO HANDLER
            if update.message and update.message.video:
                is_valid, credentials, _, _ = await check_credentials(update)
                if not is_valid:
                    clear_user_busy(user_id)
                    return
                await update.message.reply_text("sending videos is not supported")
                clear_user_busy(user_id)
                return

            # 5. DOCUMENT HANDLER
            if update.message and update.message.document:
                is_valid, credentials, _, _ = await check_credentials(update)
                if not is_valid:
                    clear_user_busy(user_id)
                    return
                await update.message.reply_text("sending documents is not supported")
                clear_user_busy(user_id)
                return

            # 6. VOICE HANDLER
            if update.message and update.message.voice:
                is_valid, credentials, _, user_info = await check_credentials(update)
                if not is_valid:
                    clear_user_busy(user_id)
                    return

                # Extract and set API key from credentials
                results = credentials.get("results", [])
                if results:
                    user_data = results[0]
                    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
                    crm_api_key = keys.get("crm_api_key")
                    if crm_api_key:
                        set_api_key(crm_api_key)

                started_at = datetime.utcnow()
                log_conversation(
                    {
                        "channel": "telegram",
                        "message_type": "voice",
                        "user": user_info,
                        "inbound": {"voice_received": True},
                        "timing": {"started_at": started_at.isoformat() + "Z"},
                    }
                )

                await update.message.reply_text(f"listening...")

                file_id = update.message.voice.file_id
                file_path = await get_telegram_file_path(file_id)

                if not file_path:
                    await update.message.reply_text(
                        "Sorry, couldn't process the voice message. Please try again or send a text."
                    )
                    clear_user_busy(user_id)
                    return

                audio_url = (
                    f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                )

                progress_bridge = TelegramProgressBridge(update.message)
                typing_task = start_typing_indicator(update.get_bot(), chat_id)

                async def send_message_callback(msg: str):
                    await progress_bridge.push(msg)

                async def transcribe_and_reply():
                    try:
                        transcribed_text = await transcribe_audio(
                            url=audio_url,
                            mime_type="audio/ogg",
                            model=VOICE_STT_MODEL,
                        )
                        if transcribed_text:
                            # await update.message.reply_text(
                            #     f"You Said:\n {transcribed_text}"
                            # )
                            log_conversation(
                                {
                                    "channel": "telegram",
                                    "message_type": "voice",
                                    "user": user_info,
                                    "inbound": {
                                        "transcribed_text": transcribed_text[:1000]
                                    },
                                }
                            )
                            # Use chat-specific session ID for conversation memory
                            session_id = get_telegram_session_id(update, user_info)
                            try:
                                result = await handle_integration_message(
                                    transcribed_text,
                                    credentials or {},  # Ensure credentials is a dict
                                    message_callback=send_message_callback,
                                    session_id=session_id,
                                    stop_key=get_telegram_stop_key(update),
                                )
                            except asyncio.CancelledError:
                                return

                            await progress_bridge.finalize()

                            if result.get("status") == "context_limit":
                                await update.message.reply_text(result["message"])
                                # Extract API key from credentials (same as integration_handler)
                                results = credentials.get("results", [])
                                if results:
                                    user_data = results[0]
                                    keys = {
                                        k["name"]: k["value"]
                                        for k in user_data.get("keys", [])
                                    }
                                    crm_api_key = keys.get("crm_api_key")

                                    if crm_api_key:
                                        set_api_key(crm_api_key)
                                    else:
                                        await update.message.reply_text(
                                            f"❌ CRM API key not found. Keys available: {list(keys.keys())}"
                                        )
                                        clear_user_busy(user_id)
                                        return
                                else:
                                    await update.message.reply_text(
                                        "❌ Invalid credentials structure."
                                    )
                                    clear_user_busy(user_id)
                                    return
                                # Reset session automatically
                                source = SessionSource(
                                    platform=Platform.TELEGRAM,
                                    chat_id=str(chat_id),
                                    chat_name=update.effective_chat.title
                                    or getattr(
                                        update.effective_chat, "full_name", None
                                    ),
                                    chat_type="dm",
                                    user_id=str(user_id)
                                    if update.effective_user
                                    else None,
                                    user_name=update.effective_user.full_name
                                    if update.effective_user
                                    else None,
                                    thread_id=str(
                                        update.effective_message.message_thread_id
                                    )
                                    if update.effective_message
                                    and update.effective_message.message_thread_id
                                    else None,
                                )
                                session_store.reset_session(source)
                                clear_api_key()  # Clean up
                                clear_user_busy(user_id)
                                return
                            if result.get("status") == "stopped":
                                return
                            outbound_messages = progress_bridge.messages
                            if not outbound_messages:
                                await _notify_debug_issue(
                                    "Blank agent response skipped",
                                    (
                                        f"user_id={user_id}\n"
                                        f"user_name={user_name}\n"
                                        f"message_type=voice\n"
                                        f"transcript={transcribed_text[:500]}"
                                    ),
                                )
                                await update.message.reply_text(
                                    "I didn't get a usable response from the agent. Please try again in a moment."
                                )
                        else:
                            await update.message.reply_text(
                                "Sorry, couldn't transcribe the voice message. Please try again or send a text."
                            )

                        completed_at = datetime.utcnow()
                        duration_seconds = (completed_at - started_at).total_seconds()
                        outbound_messages = progress_bridge.messages
                        log_conversation(
                            {
                                "channel": "telegram",
                                "message_type": "voice",
                                "user": user_info,
                                "outbound": {
                                    "messages": [
                                        msg[:500] for msg in outbound_messages
                                    ],
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
                        print(
                            f"Telegram voice transcription error for user {user_id}: {e}"
                        )
                        try:
                            await update.message.reply_text(
                                "Sorry, couldn't transcribe the voice message. Please try again or send a text."
                            )
                        except Exception:
                            pass
                    finally:
                        if typing_task:
                            await stop_typing_indicator(typing_task)
                        clear_user_busy(user_id)

                asyncio.create_task(transcribe_and_reply())
                return

            # 7. REGULAR TEXT HANDLER (INTEGRATION LOGIC)
            if update.message and update.message.text:
                user_msg = update.message.text
                is_valid, credentials, _, user_info = await check_credentials(update)
                if not is_valid:
                    clear_user_busy(user_id)
                    return

                # Extract and set API key from credentials
                results = credentials.get("results", [])
                if results:
                    user_data = results[0]
                    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}
                    crm_api_key = keys.get("crm_api_key")
                    if crm_api_key:
                        set_api_key(crm_api_key)

                await update.message.reply_text("Ok, thinking...")
                started_at = datetime.utcnow()
                log_conversation(
                    {
                        "channel": "telegram",
                        "message_type": "txt",
                        "user": user_info,
                        "inbound": {"user_msg": user_msg[:1000]},
                        "timing": {"started_at": started_at.isoformat() + "Z"},
                    }
                )

                progress_bridge = TelegramProgressBridge(update.message)
                typing_task = start_typing_indicator(update.get_bot(), chat_id)

                async def send_message_callback(msg: str):
                    await progress_bridge.push(msg)

                # Use chat-specific session ID for conversation memory
                session_id = get_telegram_session_id(update, user_info)
                try:
                    result = await handle_integration_message(
                        user_msg,
                        credentials,
                        message_callback=send_message_callback,
                        session_id=session_id,
                        stop_key=get_telegram_stop_key(update),
                    )
                except asyncio.CancelledError:
                    await stop_typing_indicator(typing_task)
                    clear_user_busy(user_id)
                    return

                await progress_bridge.finalize()

                if result.get("status") == "context_limit":
                    await update.message.reply_text(result["message"])
                    # Reset session automatically
                    # Set API key for session store
                    results = credentials.get("results", [])
                    if results:
                        user_data = results[0]
                        keys = {
                            k["name"]: k["value"] for k in user_data.get("keys", [])
                        }
                        crm_api_key = keys.get("crm_api_key")
                        if crm_api_key:
                            set_api_key(crm_api_key)

                    source = SessionSource(
                        platform=Platform.TELEGRAM,
                        chat_id=str(chat_id),
                        chat_name=update.effective_chat.title
                        or getattr(update.effective_chat, "full_name", None),
                        chat_type="dm",
                        user_id=str(user_id) if update.effective_user else None,
                        user_name=update.effective_user.full_name
                        if update.effective_user
                        else None,
                        thread_id=str(update.effective_message.message_thread_id)
                        if update.effective_message
                        and update.effective_message.message_thread_id
                        else None,
                    )
                    session_store.reset_session(source)
                    await update.message.reply_text(
                        f"✨ Session reset! Starting fresh.\n\nPrevious chat history cleared. How can I help you with the CRM today?"
                    )
                    clear_api_key()  # Clean up
                    # Cancel typing indicator
                    if typing_task:
                        typing_task.cancel()
                        try:
                            await typing_task
                        except asyncio.CancelledError:
                            pass
                    clear_user_busy(user_id)
                    return

                if result.get("status") == "stopped":
                    await stop_typing_indicator(typing_task)
                    clear_user_busy(user_id)
                    return

                outbound_messages = progress_bridge.messages
                if not outbound_messages:
                    await _notify_debug_issue(
                        "Blank agent response skipped",
                        (
                            f"user_id={user_id}\n"
                            f"user_name={user_name}\n"
                            f"message_type=txt\n"
                            f"user_msg={user_msg[:500]}"
                        ),
                    )
                    await update.message.reply_text(
                        "I didn't get a usable response from the agent. Please try again in a moment."
                    )

                completed_at = datetime.utcnow()
                duration_seconds = (completed_at - started_at).total_seconds()
                log_conversation(
                    {
                        "channel": "telegram",
                        "message_type": "txt",
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

                await stop_typing_indicator(typing_task)
                clear_user_busy(user_id)
                return

            # If no handler matched
            await update.message.reply_text(
                "Sorry, I don't understand that message type."
            )
            clear_user_busy(user_id)
            return

        except Exception as e:
            print(f"Telegram handler error for user {user_id}: {e}")
            try:
                await update.message.reply_text(get_user_facing_error_message(e))
            except Exception:
                pass  # If we can't even send the error message, just swallow it

            try:
                if TELEGRAM_BOT_TOKEN and TELEGRAM_ERROR_CHAT_ID:
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    await bot.send_message(
                        chat_id=TELEGRAM_ERROR_CHAT_ID,
                        text=f"Error for user {user_id}: {e}",
                    )
            except Exception as group_error:
                print(
                    f"Failed to send error to group {TELEGRAM_ERROR_CHAT_ID}: {group_error}"
                )

            if typing_task:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
            clear_user_busy(user_id)
            return

    except Exception as e:
        # Top-level catch-all: prevents "Task exception was never retrieved"
        # for fire-and-forget tasks created by asyncio.create_task()
        print(f"Unhandled error in telegram handler: {e}")
        return
