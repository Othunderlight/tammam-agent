import asyncio
from datetime import datetime, timedelta
from typing import Optional

from ai.utils.logger import extract_user_info
from integrations.webhook.credentials import (
    get_credentials_by_token,
    validate_credentials,
)

PROCESSING_TIMEOUT_SECONDS = 120
_user_processing_until: dict[str, datetime] = {}

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


async def check_credentials_by_token(token: str):
    """
    Check user credentials using JWT token.
    Returns (is_valid, credentials, error_message, user_info).
    """
    try:
        credentials = await get_credentials_by_token(token)
        is_valid, error = validate_credentials(credentials)

        if not is_valid:
            return False, None, error, None

        # Here we could also check for credits/can_continue if needed, 
        # similar to telegram/utils.py but maybe for webchat we skip for now 
        # or follow the same can_continue logic.
        
        # Let's check can_continue as well to stay consistent.
        results = credentials.get("results", [])
        if results:
            keys = {k["name"]: k["value"] for k in results[0].get("keys", [])}
            if keys.get("can_continue") != "1":
                return False, None, "credit_limit", extract_user_info(credentials)

        user_info = extract_user_info(credentials)
        return True, credentials, None, user_info
    except Exception as e:
        return False, None, str(e), None

async def send_webchat_message(user_id: str, message: str):
    """
    Placeholder for sending a message back to the web chat.
    This could be a call to another API or a websocket push.
    """
    # For now, we just log it or it could be implemented to call a specific endpoint
    print(f"[WebChat Outbound] User: {user_id}, Message: {message}")
    pass
