"""
Tasks API client functions.
"""

import os

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")


def list_tasks(apikey: str, **filters) -> dict:
    """
    List/search tasks.

    Args:
        apikey: API key for authentication.
        **filters: Query filters (e.g., status="Todo", search="follow", due_date__gt="2024-01-01").

    Returns:
        JSON response with tasks list.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/tasks/", headers=headers, params=filters)
        response.raise_for_status()
        return response.json()


def get_task(apikey: str, task_id: str) -> dict:
    """
    Retrieve a task by ID.

    Args:
        apikey: API key for authentication.
        task_id: UUID of the task.

    Returns:
        JSON response with task details.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.get(f"{BASE_URL}/tasks/{task_id}/", headers=headers)
        response.raise_for_status()
        return response.json()


def create_task(
    apikey: str,
    title: str,
    description: str = None,
    status: str = None,
    due_date: str = None,
    related_person: str = None,
) -> dict:
    """
    Create a new task.

    Args:
        apikey: API key for authentication.
        title: Task title (required).
        description: Detailed description.
        status: One of: Todo, In Progress, Done.
        due_date: ISO 8601 datetime (for example: 2026-02-10).
        related_person: Link to a person (UUID).

    Returns:
        JSON response with created task.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {"title": title}
    if description is not None:
        data["description"] = description
    if status is not None:
        data["status"] = status
    if due_date is not None:
        data["due_date"] = due_date
    if related_person is not None:
        data["related_person"] = related_person

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/tasks/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()


def update_task(
    apikey: str,
    task_id: str,
    title: str = None,
    description: str = None,
    status: str = None,
    due_date: str = None,
    related_person: str = None,
) -> dict:
    """
    Update a task (PATCH).

    Args:
        apikey: API key for authentication.
        task_id: UUID of the task.
        title: Task title.
        description: Detailed description.
        status: One of: Todo, In Progress, Done.
        due_date: ISO 8601 datetime (for example: 2026-02-10).
        related_person: Link to a person (UUID).

    Returns:
        JSON response with updated task.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {}
    if title is not None:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if status is not None:
        data["status"] = status
    if due_date is not None:
        data["due_date"] = due_date
    if related_person is not None:
        data["related_person"] = related_person

    with httpx.Client() as client:
        response = client.patch(
            f"{BASE_URL}/tasks/{task_id}/", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()


def delete_task(apikey: str, task_id: str) -> dict:
    """
    Delete a task.

    Args:
        apikey: API key for authentication.
        task_id: UUID of the task.

    Returns:
        JSON response with deletion status.
    """
    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client() as client:
        response = client.delete(f"{BASE_URL}/tasks/{task_id}/", headers=headers)
        response.raise_for_status()
        return {"deleted": True, "id": task_id}


def import_tasks(
    apikey: str, tasks: list[dict], auto_create_related_person: bool = False
) -> dict:
    """
    Bulk create tasks.

    Args:
        apikey: API key for authentication.
        tasks: List of task objects.
        auto_create_related_person: If True, create persons by name if they don't exist.

    Returns:
        JSON response with import results.
    """
    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }

    if auto_create_related_person:
        data = {"data": tasks, "auto_create": {"related_person": True}}
    else:
        data = tasks

    with httpx.Client() as client:
        response = client.post(f"{BASE_URL}/tasks/import/", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
