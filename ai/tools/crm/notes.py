"""
Notes API client functions.
"""

import os

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def list_notes(apikey: str, **filters) -> dict:
    """
    List/search notes.

    Args:
        apikey: API key for authentication.
        **filters: Query filters (e.g., search="pricing", title__icontains="meeting").

    Returns:
        JSON response with notes list.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/notes/", headers=headers, params=filters)
        response.raise_for_status()
        return response.json()


def get_note(apikey: str, note_id: str) -> dict:
    """
    Retrieve a note by ID.

    Args:
        apikey: API key for authentication.
        note_id: UUID of the note.

    Returns:
        JSON response with note details.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/notes/{note_id}/", headers=headers)
        response.raise_for_status()
        return response.json()


def create_note(
    apikey: str,
    title: str = None,
    content: str = None,
    related_person: str = None,
) -> dict:
    """
    Create a new note.

    Args:
        apikey: API key for authentication.
        title: Note title.
        content: Full note content.
        related_person: Link to a person (UUID).

    Returns:
        JSON response with created note.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if related_person is not None:
        data["related_person"] = related_person

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/notes/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()


def update_note(
    apikey: str,
    note_id: str,
    title: str = None,
    content: str = None,
    related_person: str = None,
) -> dict:
    """
    Update a note (PATCH).

    Args:
        apikey: API key for authentication.
        note_id: UUID of the note.
        title: Note title.
        content: Full note content.
        related_person: Link to a person (UUID).

    Returns:
        JSON response with updated note.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if title is not None:
        data["title"] = title
    if content is not None:
        data["content"] = content
    if related_person is not None:
        data["related_person"] = related_person

    with httpx.Client() as client:
        response = client.patch(
            f"{BASE_URL}/notes/{note_id}/", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()


def delete_note(apikey: str, note_id: str) -> dict:
    """
    Delete a note.

    Args:
        apikey: API key for authentication.
        note_id: UUID of the note.

    Returns:
        JSON response with deletion status.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.delete(f"{BASE_URL}/notes/{note_id}/", headers=headers)
        response.raise_for_status()
        return {"deleted": True, "id": note_id}


def import_notes(apikey: str, notes: list[dict]) -> dict:
    """
    Bulk create notes.

    Args:
        apikey: API key for authentication.
        notes: List of note objects.

    Returns:
        JSON response with import results.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/notes/import/", headers=headers, json=notes)
        response.raise_for_status()
        return response.json()
