import asyncio
import os

from telegram import Bot, Update

telegram_bot = None


async def init_telegram():
    global telegram_bot
    telegram_bot = None

    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_bot_token:
        telegram_bot = Bot(token=telegram_bot_token)


async def telegram_webhook_handler(request_json: dict):
    if not telegram_bot:
        await init_telegram()
        if not telegram_bot:
            return None

    update = Update.de_json(request_json, telegram_bot)

    from integrations.telegram.handlers import handle_telegram_message

    # Fire-and-forget: respond to Telegram immediately so it can deliver
    # the next update right away. The busy-check inside handle_telegram_message
    # will reject concurrent messages from the same user.
    asyncio.create_task(handle_telegram_message(update))

    return {"ok": True}
