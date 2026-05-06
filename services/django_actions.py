import logging
import os

import httpx
from services.gdrive import fetch_public_file_content

default_logger = logging.getLogger(__name__)

DJANGO_API_URL = os.getenv("SYSTEM_API_ENDPOINT")


async def fetch_django_context(
    client: httpx.AsyncClient, url: str, headers: dict, logger=None
) -> dict:
    log = logger or default_logger
    log.info(f"Fetching context from: {url}")
    try:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error(f"Failed to fetch context from Django: {e}")
        raise e


async def fetch_org_knowledge_base(
    client: httpx.AsyncClient, files_url: str, headers: dict, logger=None
) -> str:
    log = logger or default_logger
    knowledge_base = ""
    try:
        log.info(f"Fetching files from: {files_url}")
        files_response = await client.get(files_url, headers=headers)
        files_response.raise_for_status()
        files_data = files_response.json()

        for file_info in files_data:
            public_url = file_info.get("public_url")
            if public_url:
                log.info(f"Fetching content for file: {file_info.get('name')}")
                content = fetch_public_file_content(public_url)
                if content:
                    knowledge_base += (
                        f"\n--- File: {file_info.get('name')} ---\n{content}\n"
                    )
    except Exception as e:
        log.error(f"Failed to fetch organization files: {e}")
        pass

    return knowledge_base


async def update_django_record(
    client: httpx.AsyncClient, url: str, data: dict, headers: dict, logger=None
):
    log = logger or default_logger
    try:
        response = await client.patch(url, json=data, headers=headers)
        response.raise_for_status()
        log.info(f"Successfully updated record at {url}")
    except Exception as e:
        log.error(f"Failed to update record in Django: {e}")
        raise e


async def bulk_create_activities(
    client: httpx.AsyncClient,
    activities: list,
    person_id: str,
    headers: dict,
    logger=None,
) -> dict:
    """
    Bulk create ActivityLog entries in Django.

    Args:
        client: httpx.AsyncClient instance
        activities: List of activity dicts from AI parser
        person_id: UUID of the related person
        headers: Auth headers
        logger: Optional logger

    Returns:
        Response JSON from Django
    """
    log = logger or default_logger
    url = f"{DJANGO_API_URL}/activities/import/"

    # Attach person_id to each activity
    payload = [{**activity, "related_person": person_id} for activity in activities]

    log.info(f"Bulk creating {len(payload)} activities for person {person_id}")

    try:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        log.info(f"Successfully created {len(payload)} activities")
        return response.json()
    except Exception as e:
        log.error(f"Failed to bulk create activities: {e}")
        raise e
