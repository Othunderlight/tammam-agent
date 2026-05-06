import asyncio
import logging
import os
import warnings
from typing import Optional

import httpx
import inngest
import inngest.fast_api
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

load_dotenv()

from auth import generate_system_token, verify_token
from inngest_client import inngest_client, inngest_functions
from integrations.send_message_auth import authorize_telegram_send_message

app = FastAPI(title="FounderStack AI Service")


def configure_runtime_logging() -> None:
    """Reduce noisy third-party logs while keeping warnings/errors visible."""
    noisy_loggers = [
        "httpx",
        "httpcore",
        "mcp.client.streamable_http",
        "google_genai.types",
        "google_adk",
        "google.adk",
        "whatsmeow.Client",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    warnings.filterwarnings(
        "ignore",
        message=r"authlib\.jose module is deprecated, please use joserfc instead\.",
        category=Warning,
    )
    warnings.filterwarnings(
        "ignore",
        message=r"\[EXPERIMENTAL\] feature .* is enabled\.",
        category=UserWarning,
    )


configure_runtime_logging()

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:3000,http://127.0.0.1:8000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the Inngest endpoint
inngest.fast_api.serve(app, inngest_client, inngest_functions)

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")


@app.get("/")
async def root():
    return {"message": "FounderStack AI Service is running"}


@app.get("/is_healthy/", response_class=PlainTextResponse)
async def health_check():
    return "healthy"


# --- Logic 1: User-Triggered Request (UI) ---


@app.post("/ai/process-lead")
async def process_lead(payload: dict, user_data: dict = Depends(verify_token)):
    """
    Example of UI-triggered logic.
    Verified user sends a request, we talk to Django using THEIR token.
    """
    # In a real scenario, you'd extract the token from the request header
    # to pass it along to Django, or use the system token if preferred.
    return {
        "status": "success",
        "message": f"AI processing started for user {user_data.get('username')}",
        "data": payload,
    }


# --- Conversation Parser Endpoint ---


class ParseConversationRequest(BaseModel):
    person_id: str
    conversation_text: str
    person_name: Optional[str] = "Contact"
    channel_hint: Optional[str] = None


@app.post("/ai/parse-conversation")
async def parse_conversation_endpoint(
    request: ParseConversationRequest, user_data: dict = Depends(verify_token)
):
    """
    User-triggered conversation parsing.
    Sends to Inngest for async AI processing.
    """
    await inngest_client.send(
        inngest.Event(
            name="conversation/parse.requested",
            data={
                "person_id": request.person_id,
                "conversation_text": request.conversation_text,
                "person_name": request.person_name,
                "channel_hint": request.channel_hint,
                "user_id": user_data.get("user_id"),
            },
        )
    )
    return {"status": "processing", "message": "Conversation parsing queued"}


# --- Logic 2: Auto-Triggered Request (Background Trigger) ---


@app.post("/trigger/activity-log")
async def trigger_activity_log(data: dict):
    """
    Endpoint called by Django signals.
    Django sends data here, and this triggers an Inngest function.
    """
    print(f"Received trigger from Django: {data}")

    await inngest_client.send(inngest.Event(name="activity/log.created", data=data))

    return {"status": "received", "detail": "Background processing queued via Inngest"}


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


@app.post("/trigger/send-email")
async def trigger_send_email(request: SendEmailRequest):
    """
    Endpoint called by Django to offload email sending.
    """
    await inngest_client.send(
        inngest.Event(
            name="email/send.requested",
            data={
                "to": request.to,
                "subject": request.subject,
                "body": request.body,
            },
        )
    )
    return {"status": "received", "detail": "Email sending queued via Inngest"}


@app.get("/test-django-connection")
async def test_connection(user_data: dict = Depends(verify_token)):
    """
    Verifies that FastAPI can talk to Django using the system token.
    """
    system_token = generate_system_token()
    headers = {"Authorization": f"Bearer {system_token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{DJANGO_API_URL}/connection-test/", headers=headers
            )
            return {
                "fastapi_verified_user": user_data.get("username"),
                "django_response": response.json()
                if response.status_code == 200
                else response.text,
                "django_status": response.status_code,
            }
        except Exception as e:
            return {"error": str(e)}


# --- Telegram Webhook ---

from integrations.telegram.webhook import init_telegram, telegram_webhook_handler
from integrations.telegram.set_webhook import set_webhook, verify_webhook
from integrations.whatsapp.client import (
    init_whatsapp,
    register_whatsapp_routes,
    shutdown_whatsapp,
)

register_whatsapp_routes(app)


@app.on_event("startup")
async def startup():
    await init_telegram()
    await init_whatsapp()
    # Auto-set Telegram webhook on startup
    webhook_result = await set_webhook()
    if webhook_result["status"] != "success":
        print(f"❌ Failed to set Telegram webhook: {webhook_result['message']}")


@app.on_event("shutdown")
async def shutdown():
    await shutdown_whatsapp()


@app.post("/webhooks/telegram")
async def telegram_webhook(request: Request):
    request_json = await request.json()
    await telegram_webhook_handler(request_json)
    return {"ok": True}


class SendTelegramMessageRequest(BaseModel):
    user_id: int
    message: str


@app.post("/telegram/send-message")
async def send_telegram_message(
    request: SendTelegramMessageRequest, user_data: dict = Depends(verify_token)
):
    """Send a Telegram message to a user by their Telegram User ID."""
    from integrations.telegram.webhook import telegram_bot

    if not telegram_bot:
        return {"status": "error", "message": "Telegram bot not initialized"}

    try:
        await authorize_telegram_send_message(request.user_id, user_data)
        await telegram_bot.send_message(
            chat_id=request.user_id, text=request.message
        )
        return {"status": "success", "message": "Message sent"}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/webhooks/telegram/health")
async def telegram_webhook_health():
    """Health check endpoint for Telegram webhook configuration."""
    result = await verify_webhook()
    if result["status"] == "success":
        info = result["info"]
        return {
            "status": "healthy",
            "webhook_configured": bool(info.get("url")),
            "url": info.get("url"),
            "pending_updates": info.get("pending_update_count", 0),
            "last_error": info.get("last_error_message"),
        }
    return {
        "status": "unhealthy",
        "error": result["message"],
    }
