import asyncio
import os
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import httpx
from ai.utils.logger import extract_user_info
from chatgpt_md_converter import telegram_format
from telegram import Bot, Update
from telegram.constants import ChatAction

from integrations.telegram.credentials import (
    get_credentials_from_django,
    validate_credentials,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")


PROCESSING_TIMEOUT_SECONDS = 120

_last_processed_update_id: Optional[int] = None

_user_processing_until: dict[int, datetime] = {}

def is_duplicate_update(update: Update) -> bool:
    """Skip duplicate/old updates to prevent reprocessing."""
    global _last_processed_update_id
    if update.update_id is None:
        return False
    if (
        _last_processed_update_id is not None
        and update.update_id <= _last_processed_update_id
    ):
        return True
    _last_processed_update_id = update.update_id
    return False


def is_user_busy(user_id: int) -> bool:
    """Check if user has a message still being processed."""
    until = _user_processing_until.get(user_id)
    if until is None:
        return False
    if datetime.utcnow() > until:
        del _user_processing_until[user_id]
        return False
    return True


def set_user_busy(user_id: int) -> None:
    """Mark user as processing with 2 minute timeout."""
    _user_processing_until[user_id] = datetime.utcnow() + timedelta(
        seconds=PROCESSING_TIMEOUT_SECONDS
    )


def clear_user_busy(user_id: int) -> None:
    """Clear user processing state."""
    _user_processing_until.pop(user_id, None)


async def _typing_indicator(bot: Bot, chat_id: int) -> None:
    """Keep Telegram's typing indicator active until cancelled."""
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        print(f"Failed to update typing indicator for chat {chat_id}: {e}")


def start_typing_indicator(bot: Bot, chat_id: int) -> asyncio.Task:
    return asyncio.create_task(_typing_indicator(bot, chat_id))


async def stop_typing_indicator(typing_task: Optional[asyncio.Task]) -> None:
    if not typing_task:
        return

    typing_task.cancel()
    try:
        await typing_task
    except asyncio.CancelledError:
        pass


async def get_telegram_file_path(file_id: str) -> Optional[str]:
    """Get the file path from Telegram using the file_id."""
    if not TELEGRAM_BOT_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data["result"]["file_path"]
        except Exception:
            pass
    return None


async def forward_to_n8n(payload):
    async with httpx.AsyncClient() as client:
        await client.post(N8N_WEBHOOK_URL, json=payload)


def get_link_text_by_domain(url: str) -> str:
    """Determine link text based on domain."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if "linkedin.com" in domain:
            return "view linkedin profile"
        elif "crm.founderstack.cloud" in domain:
            return "open in CRM"
        elif "founderstack.cloud" in domain:
            return "open in FounderStack"
        else:
            return "open link"
    except Exception:
        return "open link"


def md_to_telegram_html(text: str) -> str:
    html = telegram_format(text)

    def replace_link_text(match):
        href = match.group(1)
        new_text = get_link_text_by_domain(href)
        return f'<a href="{href}">{new_text}</a>'

    html = re.sub(r'<a href="([^"]+)">[^<]+</a>', replace_link_text, html)

    url_pattern = re.compile(r'(?<!")https?://[^\s<]+(?!"})')

    def replace_bare_url(match):
        url = match.group(0).rstrip(".,;:)")
        if url and "://" in url:
            link_text = get_link_text_by_domain(url)
            return f'<a href="{url}">{link_text}</a>'
        return url

    html = url_pattern.sub(replace_bare_url, html)

    return html.strip()


def get_can_continue(credentials: dict) -> bool:
    """Extract can_continue value from credentials."""
    results = credentials.get("results", [])
    if not results:
        return False
    keys = {k["name"]: k["value"] for k in results[0].get("keys", [])}
    return keys.get("can_continue") == "1"


async def check_credentials(update: Update):
    """
    Check user credentials.
    Returns (is_valid, credentials, error_message, user_info).
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    typing_task = start_typing_indicator(update.get_bot(), chat_id)

    try:
        credentials = await get_credentials_from_django(user_id)

        is_valid, error = validate_credentials(credentials)

        if not is_valid:
            if error == "not_eligible":
                await update.message.reply_text(
                    "To connect your Telegram, please copy this ID and paste it in the CRM:\n\n"
                    f"<code>{user_id}</code>\n\n"
                    "Then click Connect Agent",
                    parse_mode="HTML",
                )
            elif error == "duplicate":
                await update.message.reply_text("error: +2c-dj 401")
            return False, None, error, None

        if not get_can_continue(credentials):
            user_info = extract_user_info(credentials)
            first_name = user_info.get("first_name", "there")
            await update.message.reply_text("Ok, thinking...")
            await asyncio.sleep(2)
            await update.message.reply_text(
                f"Hi {first_name}, this is Tmm Agent, How are you doing?\n\n"
                "You've used all your credits for this month 🚀\n\n"
                "To continue using the CRM and managing your leads, you can upgrade your plan anytime.\n\n"
                "We're currently offering an <b>early adopter offer - 50% off</b> on the yearly plan "
                "in exchange for your feedback and ideas while we improve the product.\n\n"
                '➤ <a href="https://www.founderstack.cloud/offer">See the early adopter offer</a>\n\n'
                "If you want help choosing the right plan or have questions, you can chat directly with the founder Omar.\n"
                'on <a href="https://t.me/Omar_Gatara">Telegram</a> or <a href="https://wa.me/+963939676801">WhatsApp</a>',
                parse_mode="HTML",
            )
            return False, None, "cant continue", None

        user_info = extract_user_info(credentials)
        return True, credentials, None, user_info
    finally:
        await stop_typing_indicator(typing_task)
