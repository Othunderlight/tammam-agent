import os
from typing import Any

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def manage_user_profile(
    apikey: str, content: str, append: bool = True
) -> dict[str, Any]:
    """
    Manage the user profile block in preferences.

    Args:
        apikey: API key for authentication.
        content: The content to set or append to the user profile.
        append: If True, appends to existing profile. If False, replaces it. Default is True.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {apikey}"}
    url = f"{BASE_URL.rstrip('/')}/user-preferences/my-preferences/"

    payload = {"name": "USER_PROFILE_BLOCK", "value": content, "append": append}

    with httpx.Client(follow_redirects=True) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
