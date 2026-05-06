import os
from typing import Optional

import httpx
from fastapi import HTTPException

from integrations.telegram.credentials import (
    get_credentials_from_django as get_telegram_credentials_from_django,
    validate_credentials as validate_telegram_credentials,
)
from integrations.whatsapp.credentials import (
    get_credentials_from_django as get_whatsapp_credentials_from_django,
    validate_credentials as validate_whatsapp_credentials,
)

SYSTEM_API_ENDPOINT = os.getenv("SYSTEM_API_ENDPOINT")


def _extract_crm_api_key(credentials: dict) -> Optional[str]:
    """Extract the CRM API key from a credential payload."""
    results = credentials.get("results", [])
    if not results:
        return None

    keys = {key["name"]: key["value"] for key in results[0].get("keys", [])}
    return keys.get("crm_api_key")


def _get_request_api_key(user_data: dict) -> str:
    """Return the API key used on the current request or reject the request."""
    if user_data.get("auth_method") != "api_key":
        raise HTTPException(
            status_code=403,
            detail="This endpoint requires the owner's CRM API key.",
        )

    api_key = user_data.get("api_key")
    if not api_key:
        raise HTTPException(status_code=403, detail="Missing request API key.")

    return api_key


def _get_request_headers(user_data: dict) -> dict:
    """Build Django auth headers from the current authenticated request."""
    auth_method = user_data.get("auth_method")

    if auth_method == "api_key":
        api_key = user_data.get("api_key")
        if not api_key:
            raise HTTPException(status_code=403, detail="Missing request API key.")
        return {"Authorization": f"Api-Key {api_key}"}

    if auth_method == "jwt":
        token = user_data.get("token")
        if not token:
            raise HTTPException(status_code=403, detail="Missing request token.")
        return {"Authorization": f"Bearer {token}"}

    raise HTTPException(status_code=403, detail="Unsupported authentication method.")


async def _is_staff_user(user_data: dict) -> bool:
    """Return whether the current authenticated user is staff in Django."""
    headers = _get_request_headers(user_data)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SYSTEM_API_ENDPOINT}/users/is-staff/",
                headers=headers,
            )
            response.raise_for_status()
        except Exception as exc:
            raise HTTPException(
                status_code=403,
                detail=f"Could not verify staff access: {exc}",
            )

    payload = response.json()
    return bool(payload.get("is_staff"))


def _validate_credentials_match_request(credentials: dict, request_api_key: str) -> None:
    """Ensure the integration credential belongs to the requesting CRM API key."""
    credential_api_key = _extract_crm_api_key(credentials)
    if not credential_api_key:
        raise HTTPException(
            status_code=403,
            detail="Credential is missing its CRM API key binding.",
        )

    if credential_api_key != request_api_key:
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to use this integration credential.",
        )


async def authorize_telegram_send_message(user_id: int, user_data: dict) -> None:
    """Authorize Telegram send-message requests against the stored CRM API key."""
    credentials = await get_telegram_credentials_from_django(user_id)
    is_valid, error = validate_telegram_credentials(credentials)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=f"Telegram credential is not eligible for messaging: {error}",
        )

    if await _is_staff_user(user_data):
        return None

    request_api_key = _get_request_api_key(user_data)
    _validate_credentials_match_request(credentials, request_api_key)
    return None


async def authorize_whatsapp_send_message(
    phone_number: str, user_data: dict
) -> None:
    """Authorize WhatsApp send-message requests against the stored CRM API key."""
    credentials = await get_whatsapp_credentials_from_django(phone_number)
    is_valid, error = validate_whatsapp_credentials(credentials)

    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=f"WhatsApp credential is not eligible for messaging: {error}",
        )

    if await _is_staff_user(user_data):
        return None

    request_api_key = _get_request_api_key(user_data)
    _validate_credentials_match_request(credentials, request_api_key)
    return None
