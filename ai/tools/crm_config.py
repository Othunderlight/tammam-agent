"""
CRM Config fetcher - gets user-specific config to render agent prompt.
"""

import os

import httpx

from ai.tools.crm_context import get_api_key

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def get_crm_config() -> dict:
    """
    Fetch CRM config for the current user (based on API key in context).
    Returns stage_choices, type_choices, interaction_types, etc.
    """
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API key not set in context")

    headers = {"Authorization": f"Api-Key {api_key}"}

    with httpx.Client(follow_redirects=True) as client:
        response = client.get(f"{BASE_URL}/config/mine", headers=headers)
        response.raise_for_status()
        result = response.json()
        # Ensure we return a dict
        if not isinstance(result, dict):
            print(
                f"Warning: CRM config API returned non-dict: {type(result)} - {result}"
            )
            return {}

        result["pipeline_stages"] = [
            stage.get("label") for stage in result.get("pipeline_stages", [])
        ]
        result["lead_types"] = [
            lead_type.get("label") for lead_type in result.get("lead_types", [])
        ]
        result["lead_sources"] = [
            source.get("label") for source in result.get("lead_sources", [])
        ]

        # Fetch interaction types
        types_response = client.get(f"{BASE_URL}/interaction-types/", headers=headers)
        if types_response.status_code == 200:
            types = types_response.json()
            if isinstance(types, list):
                types_list = types
            elif isinstance(types, dict) and "results" in types:
                types_list = types["results"]
            else:
                types_list = []

            if types_list:
                result["interaction_types"] = [
                    f"{t.get('name')} ({t.get('id')}) : {t.get('description')}"
                    if t.get("description")
                    else f"{t.get('name')} ({t.get('id')})"
                    for t in types_list
                ]

        return result
