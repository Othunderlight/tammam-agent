"""
People API client functions.
"""

import os

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def list_people(apikey: str, **filters) -> dict:
    """
    List/search people (leads and contacts).

    Args:
        apikey: API key for authentication.
        **filters: Query filters (e.g., search="ahmed", city="Dubai", stage="Qualified").

    Returns:
        JSON response with people list.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/people/", headers=headers, params=filters)
        response.raise_for_status()
        return response.json()


def get_person(apikey: str, person_id: str) -> dict:
    """
    Retrieve a person by ID.

    Args:
        apikey: API key for authentication.
        person_id: UUID of the person.

    Returns:
        JSON response with person details.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/people/{person_id}/", headers=headers)
        response.raise_for_status()
        return response.json()


def get_person_context(apikey: str, person_id: str, sections: str = "all") -> dict:
    """
    Get related data for a person (tasks, notes, activities).

    Args:
        apikey: API key for authentication.
        person_id: UUID of the person.
        sections: Comma-separated list: "general", "notes", "context", "tasks" or "all".

    Returns:
        JSON response with context data.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}
    params = {"sections": sections}

    with httpx.Client() as client:
        response = client.get(
            f"{BASE_URL}/people/{person_id}/context/", headers=headers, params=params
        )
        response.raise_for_status()
        return response.json()


def create_person(
    apikey: str,
    name: str,
    email: str = None,
    phone: str = None,
    job_title: str = None,
    city: str = None,
    linkedin: str = None,
    conversion_rate: int = None,
    stage: str = None,
    lead_type: str = None,
    lead_source: str = None,
    last_action: str = None,
    recommended_action: str = None,
    company: str = None,
) -> dict:
    """
    Create a new person.

    Args:
        apikey: API key for authentication.
        name: The full name of the person (required).
        email: Professional or personal email address.
        phone: Contact phone number.
        job_title: Their current role.
        city: Current city or region.
        linkedin: URL to their LinkedIn profile.
        conversion_rate: Numerical value (0-100) representing probability.
        stage: Current stage in the pipeline.
        lead_type: Type of lead.
        lead_source: Whether the lead is Inbound or Outbound.
        last_action: Description of the last action taken.
        recommended_action: Suggested next action.
        company: Link to a company (UUID).

    Returns:
        JSON response with created person.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {"name": name}
    if email is not None:
        data["email"] = email
    if phone is not None:
        data["phone"] = phone
    if job_title is not None:
        data["job_title"] = job_title
    if city is not None:
        data["city"] = city
    if linkedin is not None:
        data["linkedin"] = linkedin
    if conversion_rate is not None:
        data["conversion_rate"] = conversion_rate
    if stage is not None:
        data["stage"] = stage
    if lead_type is not None:
        data["lead_type"] = lead_type
    if lead_source is not None:
        data["lead_source"] = lead_source
    if last_action is not None:
        data["last_action"] = last_action
    if recommended_action is not None:
        data["recommended_action"] = recommended_action
    if company is not None:
        data["company"] = company

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/people/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()


def update_person(
    apikey: str,
    person_id: str,
    name: str = None,
    email: str = None,
    phone: str = None,
    job_title: str = None,
    city: str = None,
    linkedin: str = None,
    conversion_rate: int = None,
    stage: str = None,
    lead_type: str = None,
    lead_source: str = None,
    last_action: str = None,
    recommended_action: str = None,
    company: str = None,
) -> dict:
    """
    Update a person (PATCH).

    Args:
        apikey: API key for authentication.
        person_id: UUID of the person.
        name: The full name of the person.
        email: Professional or personal email address.
        phone: Contact phone number.
        job_title: Their current role.
        city: Current city or region.
        linkedin: URL to their LinkedIn profile.
        conversion_rate: Numerical value (0-100) representing probability.
        stage: Current stage in the pipeline.
        lead_type: Type of lead.
        lead_source: Whether the lead is Inbound or Outbound.
        last_action: Description of the last action taken.
        recommended_action: Suggested next action.
        company: Link to a company (UUID).

    Returns:
        JSON response with updated person.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if name is not None:
        data["name"] = name
    if email is not None:
        data["email"] = email
    if phone is not None:
        data["phone"] = phone
    if job_title is not None:
        data["job_title"] = job_title
    if city is not None:
        data["city"] = city
    if linkedin is not None:
        data["linkedin"] = linkedin
    if conversion_rate is not None:
        data["conversion_rate"] = conversion_rate
    if stage is not None:
        data["stage"] = stage
    if lead_type is not None:
        data["lead_type"] = lead_type
    if lead_source is not None:
        data["lead_source"] = lead_source
    if last_action is not None:
        data["last_action"] = last_action
    if recommended_action is not None:
        data["recommended_action"] = recommended_action
    if company is not None:
        data["company"] = company

    with httpx.Client() as client:
        response = client.patch(
            f"{BASE_URL}/people/{person_id}/", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()


def delete_person(apikey: str, person_id: str) -> dict:
    """
    Delete a person.

    Args:
        apikey: API key for authentication.
        person_id: UUID of the person.

    Returns:
        JSON response with deletion status.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.delete(f"{BASE_URL}/people/{person_id}/", headers=headers)
        response.raise_for_status()
        return {"deleted": True, "id": person_id}


def import_people(
    apikey: str, people: list[dict], auto_create_company: bool = False
) -> dict:
    """
    Bulk create people.

    Args:
        apikey: API key for authentication.
        people: List of person objects.
        auto_create_company: If True, create companies by name if they don't exist.

    Returns:
        JSON response with import results.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }

    if auto_create_company:
        data = {"data": people, "auto_create": {"company": True}}
    else:
        data = people

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/people/import/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
