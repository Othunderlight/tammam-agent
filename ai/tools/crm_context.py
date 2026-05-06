from contextvars import ContextVar
from typing import Optional

_api_key_var: ContextVar[Optional[str]] = ContextVar("api_key", default=None)


def get_api_key() -> Optional[str]:
    """Get the API key from current context."""
    return _api_key_var.get()


# use this in testing for debug with adk cli
# def get_api_key() -> Optional[str]:
#     """Get the API key from context, fallback to environment variable."""
#     # First check context (used by FastAPI)
#     key = _api_key_var.get()
#     if key:
#         return key

#     # Fallback to environment variable (useful for ADK CLI testing)
#     return "-MD3PK4A3l49M9FlhFzqcilJXFD866Rjss-btXj1f8g"


def set_api_key(key: str) -> None:
    """Set the API key in current context."""
    _api_key_var.set(key)


def clear_api_key() -> None:
    """Clear the API key from context."""
    _api_key_var.set(None)


class ApiKeyContext:
    """Context manager for API key."""

    def __init__(self, key: str):
        self.key = key

    def __enter__(self):
        set_api_key(self.key)
        return self

    def __exit__(self, *args):
        clear_api_key()

    async def __aenter__(self):
        set_api_key(self.key)
        return self

    async def __aexit__(self, *args):
        clear_api_key()
