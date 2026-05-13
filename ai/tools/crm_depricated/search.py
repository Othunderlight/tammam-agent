"""
Global Search API client function.
"""

import os

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def global_search(apikey: str, q: str) -> dict:
    """
    Unified cross-model search across People, Companies, Tasks, and Notes.

    Args:
        apikey: API key for authentication.
        q: The search query string.

    Returns:
        JSON response with relevance-scored results from all models.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/search/", headers=headers, params={"q": q})
        response.raise_for_status()
        return response.json()
