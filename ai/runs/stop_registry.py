import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass
class ActiveRun:
    task: asyncio.Task
    stop_requested: bool = False


_active_runs: dict[str, ActiveRun] = {}


def register_active_run(run_key: str, task: asyncio.Task) -> None:
    """Track the currently running task for a run key."""
    _active_runs[run_key] = ActiveRun(task=task, stop_requested=False)


def unregister_active_run(run_key: str, task: Optional[asyncio.Task] = None) -> None:
    """Remove the tracked task if it is still the current one."""
    active_run = _active_runs.get(run_key)
    if not active_run:
        return

    if task is not None and active_run.task is not task:
        return

    _active_runs.pop(run_key, None)


def is_stop_requested(run_key: str) -> bool:
    """Return whether a stop was requested for the run key."""
    active_run = _active_runs.get(run_key)
    return bool(active_run and active_run.stop_requested)


def request_stop(run_key: str) -> bool:
    """Mark a run as stopped and cancel its running task."""
    active_run = _active_runs.get(run_key)
    if not active_run:
        return False

    active_run.stop_requested = True
    active_run.task.cancel()
    return True
