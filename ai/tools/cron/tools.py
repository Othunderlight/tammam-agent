"""
Cron Job API client functions for Hermes Agent.
"""

import os
from typing import Any, List, Optional, Union

import httpx

BASE_URL = os.getenv("SYSTEM_API_ENDPOINT")

# Built-in Hermes Cron Prompt
HERMES_CRON_PROMPT = (
    "You are running as a scheduled cron job. There is no user present — you "
    "cannot ask questions, request clarification, or wait for follow-up. Execute "
    "the task fully and autonomously, making reasonable decisions where needed. "
    "Your final response is automatically delivered to the job's configured "
    "destination — put the primary content directly in your response."
)


def list_cron_jobs(apikey: str, include_disabled: bool = False) -> dict:
    """
    List all cron jobs.

    Args:
        apikey: API key for authentication.
        include_disabled: Whether to include disabled jobs in the list.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {apikey}"}
    params = {"include_disabled": include_disabled}

    with httpx.Client(follow_redirects=True) as client:
        response = client.get(
            f"{BASE_URL.rstrip('/')}/integrations/crons/", headers=headers, params=params
        )
        response.raise_for_status()
        return response.json()


def get_cron_job(apikey: str, job_id: str) -> dict:
    """
    Retrieve a cron job by ID.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to retrieve.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client(follow_redirects=True) as client:
        response = client.get(
            f"{BASE_URL.rstrip('/')}/integrations/crons/{job_id}/", headers=headers
        )
        response.raise_for_status()
        return response.json()


def create_cron_job(
    apikey: str,
    name: str,
    prompt: str,
    schedule: str,  # e.g. "0 17 * * *" or "30m"
    skills: List[str] = None,
    model: str = None,
    provider: str = None,
    base_url: str = None,
    deliver: str = "local",
    repeat_times: int = None,
    no_agent: bool = False,
    script: str = None,
    workdir: str = None,
) -> dict:
    """
    Create a new cron job.

    Args:
        apikey: API key for authentication.
        name: Name of the cron job.
        prompt: The prompt for the agent.
        schedule: Cron schedule or interval.
        skills: List of skills required for the job.
        model: Model to use for the job.
        provider: Provider of the model.
        base_url: Base URL for the model API.
        deliver: Destination for the output (e.g., "local").
        repeat_times: Number of times to repeat the job.
        no_agent: If True, executes as a script without an agent.
        script: Script to run if no_agent is True.
        workdir: Working directory for the script.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }
    data = {
        "name": name,
        "prompt": prompt,
        "schedule": schedule,
        "deliver": deliver,
        "no_agent": no_agent,
    }
    if skills:
        data["skills"] = skills
    if model:
        data["model"] = model
    if provider:
        data["provider"] = provider
    if base_url:
        data["base_url"] = base_url
    if repeat_times is not None:
        data["repeat_times"] = repeat_times
    if script:
        data["script"] = script
    if workdir:
        data["workdir"] = workdir

    with httpx.Client(follow_redirects=True) as client:
        response = client.post(
            f"{BASE_URL.rstrip('/')}/integrations/crons/", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()


def update_cron_job(apikey: str, job_id: str, **updates) -> dict:
    """
    Update an existing cron job.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to update.
        **updates: Fields to update.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {
        "Authorization": f"Api-Key {apikey}",
        "Content-Type": "application/json",
    }

    with httpx.Client(follow_redirects=True) as client:
        response = client.patch(
            f"{BASE_URL.rstrip('/')}/integrations/crons/{job_id}/", headers=headers, json=updates
        )
        response.raise_for_status()
        return response.json()


def delete_cron_job(apikey: str, job_id: str) -> dict:
    """
    Delete a cron job.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to delete.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client(follow_redirects=True) as client:
        response = client.delete(
            f"{BASE_URL.rstrip('/')}/integrations/crons/{job_id}/", headers=headers
        )
        response.raise_for_status()
        return {"deleted": True, "id": job_id}


def pause_cron_job(apikey: str, job_id: str, reason: str = None) -> dict:
    """
    Pause a cron job.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to pause.
        reason: Optional reason for pausing.
    """
    return update_cron_job(apikey, job_id, state="paused", paused_reason=reason)


def resume_cron_job(apikey: str, job_id: str) -> dict:
    """
    Resume a paused cron job.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to resume.
    """
    return update_cron_job(apikey, job_id, state="scheduled")


def trigger_cron_job(apikey: str, job_id: str) -> dict:
    """
    Manually trigger a cron job to run now.

    Args:
        apikey: API key for authentication.
        job_id: The ID of the cron job to trigger.
    """
    if not BASE_URL:
        raise ValueError("SYSTEM_API_ENDPOINT not set")

    headers = {"Authorization": f"Api-Key {apikey}"}

    with httpx.Client(follow_redirects=True) as client:
        response = client.post(
            f"{BASE_URL.rstrip('/')}/integrations/crons/{job_id}/trigger/", headers=headers
        )
        response.raise_for_status()
        return response.json()
