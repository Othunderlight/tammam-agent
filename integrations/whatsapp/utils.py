import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional

from ai.utils.logger import extract_user_info
from neonize.aioze.client import NewAClient
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message as WAMessage
from neonize.utils.enum import ChatPresence, ChatPresenceMedia

from integrations.whatsapp.credentials import (
    get_credentials_from_django,
    validate_credentials,
)

PROCESSING_TIMEOUT_SECONDS = 120

_user_processing_until: dict[str, datetime] = {}


def md_to_whatsapp_text(text: str) -> str:
    """Convert common Markdown patterns into WhatsApp-friendly text."""
    if not text:
        return ""

    formatted = text

    # WhatsApp does not support Markdown links with custom labels.
    formatted = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda match: (
            match.group(2)
            if match.group(1).strip() == match.group(2).strip()
            else f"{match.group(1).strip()}: {match.group(2).strip()}"
        ),
        formatted,
    )

    formatted = re.sub(r"(?m)^#{1,6}\s*", "", formatted)
    formatted = re.sub(r"\*\*(.+?)\*\*", r"*\1*", formatted)
    formatted = re.sub(r"__(.+?)__", r"*\1*", formatted)
    formatted = re.sub(r"~~(.+?)~~", r"~\1~", formatted)
    formatted = re.sub(r"`([^`\n]+)`", r"```\1```", formatted)

    return formatted.strip()


def is_user_busy(user_id: str) -> bool:
    """Check if user has a message still being processed."""
    until = _user_processing_until.get(user_id)
    if until is None:
        return False
    if datetime.utcnow() > until:
        del _user_processing_until[user_id]
        return False
    return True


def set_user_busy(user_id: str) -> None:
    """Mark user as processing with 2 minute timeout."""
    _user_processing_until[user_id] = datetime.utcnow() + timedelta(
        seconds=PROCESSING_TIMEOUT_SECONDS
    )


def clear_user_busy(user_id: str) -> None:
    """Clear user processing state."""
    _user_processing_until.pop(user_id, None)


async def _typing_indicator(client: NewAClient, chat_jid) -> None:
    """Keep WhatsApp typing indicator active until cancelled."""
    try:
        while True:
            await client.send_chat_presence(
                chat_jid,
                ChatPresence.CHAT_PRESENCE_COMPOSING,
                ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT,
            )
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Failed to update WhatsApp typing indicator for chat {chat_jid}: {e}")


def start_typing_indicator(client: NewAClient, chat_jid) -> asyncio.Task:
    return asyncio.create_task(_typing_indicator(client, chat_jid))


async def stop_typing_indicator(
    client: NewAClient, chat_jid, typing_task: Optional[asyncio.Task]
) -> None:
    if typing_task:
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    try:
        await client.send_chat_presence(
            chat_jid,
            ChatPresence.CHAT_PRESENCE_PAUSED,
            ChatPresenceMedia.CHAT_PRESENCE_MEDIA_TEXT,
        )
    except Exception:
        pass


def get_can_continue(credentials: dict) -> bool:
    """Extract can_continue value from credentials."""
    results = credentials.get("results", [])
    if not results:
        return False
    keys = {k["name"]: k["value"] for k in results[0].get("keys", [])}
    return keys.get("can_continue") == "1"


async def send_text(client: NewAClient, chat_jid, text: str):
    """Send a plain conversation message."""
    return await client.send_message(chat_jid, md_to_whatsapp_text(text))


async def edit_text(client: NewAClient, chat_jid, message_id: str, text: str) -> None:
    """Edit a WhatsApp message in place."""
    await client.edit_message(
        chat_jid,
        message_id,
        WAMessage(conversation=md_to_whatsapp_text(text)),
    )


async def reply_text(client: NewAClient, event, text: str):
    """Reply to a specific inbound message."""
    return await client.reply_message(md_to_whatsapp_text(text), event)


async def check_credentials(client: NewAClient, event, sender_id: str, chat_id: str):
    """
    Check user credentials.
    Returns (is_valid, credentials, error_message, user_info).
    """
    typing_task = start_typing_indicator(client, event.Info.MessageSource.Chat)

    try:
        credentials = await get_credentials_from_django(sender_id)
        is_valid, error = validate_credentials(credentials)

        if not is_valid:
            if error == "not_eligible":
                await reply_text(
                    client,
                    event,
                    "🚫 Access denied.\n\n"
                    f"Your WhatsApp ID is:\n{chat_id}\n\n"
                    "Please paste it in the CRM and connect the agent.",
                )
            elif error == "duplicate":
                await reply_text(client, event, "error: +2c-dj 401")
            return False, None, error, None

        if not get_can_continue(credentials):
            user_info = extract_user_info(credentials)
            first_name = user_info.get("first_name", "there")
            await reply_text(client, event, "Ok, thinking...")
            await asyncio.sleep(2)
            await reply_text(
                client,
                event,
                f"Hi {first_name}, this is Tmm Agent, How are you doing?\n\n"
                "You've used all your credits for this month.\n\n"
                "To continue using the CRM and managing your leads, you can upgrade your plan anytime.\n\n"
                "We're currently offering an early adopter offer: 50% off on the yearly plan "
                "in exchange for your feedback and ideas while we improve the product.\n\n"
                "Offer: https://www.founderstack.cloud/offer\n\n"
                "If you want help choosing the right plan or have questions, you can chat directly with Omar:\n"
                "Telegram: https://t.me/Omar_Gatara\n"
                "WhatsApp: https://wa.me/+963939676801",
            )
            return False, None, "cant continue", None

        user_info = extract_user_info(credentials)
        return True, credentials, None, user_info
    finally:
        await stop_typing_indicator(client, event.Info.MessageSource.Chat, typing_task)
