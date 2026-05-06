"""
Companies API client functions.
"""

import os

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def list_companies(apikey: str, **filters) -> dict:
    """
    List/search companies.

    Args:
        apikey: API key for authentication.
        **filters: Query filters (e.g., search="term", location__icontains="dubai", icp=true).

    Returns:
        JSON response with companies list.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/companies/", headers=headers, params=filters)
        response.raise_for_status()
        return response.json()


def get_company(apikey: str, company_id: str) -> dict:
    """
    Retrieve a company by ID.

    Args:
        apikey: API key for authentication.
        company_id: UUID of the company.

    Returns:
        JSON response with company details.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/companies/{company_id}/", headers=headers)
        response.raise_for_status()
        return response.json()


def create_company(
    apikey: str,
    name: str = None,
    domain: str = None,
    location: str = None,
    employees: str = None,
    icp: bool = None,
) -> dict:
    """
    Create a new company.

    Args:
        apikey: API key for authentication.
        name: Company name.
        domain: For example: google.com
        location: Office location.
        employees: Employee count or range (for example: 500-1000).
        icp: Matches your ideal customer profile (Boolean).

    Returns:
        JSON response with created company.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if name is not None:
        data["name"] = name
    if domain is not None:
        data["domain"] = domain
    if location is not None:
        data["location"] = location
    if employees is not None:
        data["employees"] = employees
    if icp is not None:
        data["icp"] = icp

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/companies/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()


def update_company(
    apikey: str,
    company_id: str,
    name: str = None,
    domain: str = None,
    location: str = None,
    employees: str = None,
    icp: bool = None,
) -> dict:
    """
    Update a company (PATCH).

    Args:
        apikey: API key for authentication.
        company_id: UUID of the company.
        name: Company name.
        domain: For example: google.com
        location: Office location.
        employees: Employee count or range (for example: 500-1000).
        icp: Matches your ideal customer profile (Boolean).

    Returns:
        JSON response with updated company.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if name is not None:
        data["name"] = name
    if domain is not None:
        data["domain"] = domain
    if location is not None:
        data["location"] = location
    if employees is not None:
        data["employees"] = employees
    if icp is not None:
        data["icp"] = icp

    with httpx.Client() as client:
        response = client.patch(
            f"{BASE_URL}/companies/{company_id}/", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()


def delete_company(apikey: str, company_id: str) -> dict:
    """
    Delete a company.

    Args:
        apikey: API key for authentication.
        company_id: UUID of the company.

    Returns:
        JSON response with deletion status.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.delete(f"{BASE_URL}/companies/{company_id}/", headers=headers)
        response.raise_for_status()
        return {"deleted": True, "id": company_id}


def import_companies(apikey: str, companies: list[dict]) -> dict:
    """
    Bulk create companies.

    Args:
        apikey: API key for authentication.
        companies: List of company objects.

    Returns:
        JSON response with import results.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }

    with httpx.Client() as client:
        response = client.post(
            f"{BASE_URL}/companies/import/", headers=headers, json=companies
        )
        response.raise_for_status()
        return response.json()
