import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL")


async def set_webhook() -> dict:
    """
    Set Telegram webhook with proper error handling and configuration.
    
    Returns:
        dict: Status and message
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not found"}

    if not WEBHOOK_URL:
        return {"status": "error", "message": "TELEGRAM_WEBHOOK_URL not found"}

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,  # Drop old updates on startup
            allowed_updates=["message", "callback_query"],  # Only receive needed updates
        )
        
        # Verify webhook is set
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url == WEBHOOK_URL:
            return {
                "status": "success",
                "message": f"Webhook set to: {WEBHOOK_URL}",
                "info": {
                    "has_custom_certificate": webhook_info.has_custom_certificate,
                    "pending_update_count": webhook_info.pending_update_count,
                    "last_error_date": webhook_info.last_error_date,
                    "last_error_message": webhook_info.last_error_message,
                }
            }
        else:
            return {"status": "error", "message": "Webhook verification failed"}
            
    except Exception as e:
        return {"status": "error", "message": f"Failed to set webhook: {str(e)}"}


async def verify_webhook() -> dict:
    """
    Verify webhook configuration.
    """
    if not TELEGRAM_BOT_TOKEN:
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN not found"}

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        webhook_info = await bot.get_webhook_info()
        return {
            "status": "success",
            "info": {
                "url": webhook_info.url,
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count,
                "last_error_date": webhook_info.last_error_date,
                "last_error_message": webhook_info.last_error_message,
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to verify webhook: {str(e)}"}


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("=== Telegram Webhook Setup ===")
        
        # Set webhook
        result = await set_webhook()
        print(f"\nWebhook Setup: {result['status']}")
        if "message" in result:
            print(f"Message: {result['message']}")
        if "info" in result:
            print("\nWebhook Info:")
            for key, value in result["info"].items():
                print(f"  {key}: {value}")
        
        # Verify
        print("\n=== Verifying Webhook ===")
        verify_result = await verify_webhook()
        print(f"Verification: {verify_result['status']}")
        if "info" in verify_result:
            print("\nCurrent Configuration:")
            for key, value in verify_result["info"].items():
                print(f"  {key}: {value}")

    asyncio.run(main())
