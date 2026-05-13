"""
User preferences fetcher for prompt customization.
"""

import os
from typing import Any

import httpx
from ai.tools.manage_api_key import get_api_key

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def get_my_preferences() -> dict[str, Any]:
    """
    Fetch the current user's preferences.

    Returns:
        Dict mapping preference names to their values.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key not set in context")

    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {api_key}"}
    url = f"{BASE_URL.rstrip('/')}/user-preferences/my-preferences/"

    with httpx.Client(follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()

    if not isinstance(result, dict):
        print(
            f"Warning: user preferences API returned non-dict: {type(result)} - {result}"
        )
        return {}

    preferences = result.get("preferences", [])
    if not isinstance(preferences, list):
        print(
            "Warning: user preferences API returned invalid preferences payload: "
            f"{type(preferences)} - {preferences}"
        )
        return {}

    mapped_preferences: dict[str, Any] = {}
    for preference in preferences:
        if not isinstance(preference, dict):
            continue

        name = preference.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        mapped_preferences[name] = preference.get("value")

    return mapped_preferences


# tools
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
