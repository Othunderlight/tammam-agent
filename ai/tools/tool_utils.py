import asyncio
import inspect
from typing import Any, Callable, Dict, Optional

import httpx

from ai.tools.manage_api_key import get_api_key


def _safe_json(response: httpx.Response):
    """Best-effort JSON decoding for API error payloads."""
    try:
        result = response.json()
        # Ensure we return a dict or list, not a string
        if isinstance(result, (dict, list)):
            return result
        else:
            print(
                f"Warning: API returned non-dict/list JSON: {type(result)} - {result}"
            )
            return {"error": "Invalid response format", "raw_response": str(result)}
    except ValueError:
        return None


def _build_http_error_result(error: Exception) -> dict:
    """Return HTTP/tool errors as data so the agent can decide what to do next."""
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        payload = _safe_json(response)
        result = {
            "ok": False,
            "error_type": "http_status_error",
            "status_code": response.status_code,
            "method": response.request.method,
            "url": str(response.request.url),
            "detail": str(error),
        }
        if payload is not None:
            result["response"] = payload
        else:
            result["response_text"] = response.text[:1000]
        return result

    if isinstance(error, httpx.RequestError):
        request = error.request
        return {
            "ok": False,
            "error_type": "request_error",
            "method": request.method if request else None,
            "url": str(request.url) if request else None,
            "detail": str(error),
        }

    return {
        "ok": False,
        "error_type": "tool_error",
        "detail": str(error),
    }


class ToolWrapper:
    """
    Wrapper class that hides apikey from function signature.
    The agent will only see parameters other than apikey.
    """

    def __init__(self, func: Callable, is_async: bool = False):
        self._func = func
        self._is_async = is_async

        # Create clean signature without apikey
        original_sig = inspect.signature(func)
        new_params = [p for p in original_sig.parameters.values() if p.name != "apikey"]
        self.__signature__ = inspect.Signature(parameters=new_params)

        # Clean docstring to remove apikey references
        clean_doc = func.__doc__ or ""
        clean_doc = clean_doc.replace(
            "    Args:\n        apikey: API key for authentication.\n", ""
        )
        clean_doc = clean_doc.replace(
            "Args:\n        apikey: API key for authentication.\n", ""
        )
        self.__doc__ = clean_doc
        self.__name__ = func.__name__

    def __call__(self, *args, **kwargs):
        api_key = get_api_key()
        if not api_key:
            raise ValueError("API key not set in context. Use set_api_key() first.")
        try:
            result = self._func(api_key, *args, **kwargs)
            # Ensure result is a dict
            if not isinstance(result, dict):
                print(
                    f"Warning: Tool {self.__name__} returned non-dict: {type(result)} - {result}"
                )
                return {"error": "Tool returned invalid format", "result": str(result)}
            return result
        except (httpx.HTTPStatusError, httpx.RequestError) as error:
            return _build_http_error_result(error)
        except Exception as e:
            print(f"Unexpected error in tool {self.__name__}: {e}")
            return {"error": "Tool execution failed", "detail": str(e)}

    async def call_async(self, *args, **kwargs):
        api_key = get_api_key()
        if not api_key:
            raise ValueError("API key not set in context. Use set_api_key() first.")
        try:
            result = await self._func(api_key, *args, **kwargs)
            # Ensure result is a dict
            if not isinstance(result, dict):
                print(
                    f"Warning: Tool {self.__name__} returned non-dict: {type(result)} - {result}"
                )
                return {"error": "Tool returned invalid format", "result": str(result)}
            return result
        except (httpx.HTTPStatusError, httpx.RequestError) as error:
            return _build_http_error_result(error)
        except Exception as e:
            print(f"Unexpected error in tool {self.__name__}: {e}")
            return {"error": "Tool execution failed", "detail": str(e)}


def wrap_with_api_key(func: Callable) -> Callable:
    """Wrap a function to inject API key from context, hiding it from signature."""
    is_async = asyncio.iscoroutinefunction(func)
    wrapper = ToolWrapper(func, is_async)

    if is_async:

        async def wrapped(*args, **kwargs):
            return await wrapper.call_async(*args, **kwargs)

        wrapped.__signature__ = wrapper.__signature__
        wrapped.__doc__ = wrapper.__doc__
        wrapped.__name__ = wrapper.__name__
        return wrapped
    else:

        def wrapped(*args, **kwargs):
            return wrapper(*args, **kwargs)

        wrapped.__signature__ = wrapper.__signature__
        wrapped.__doc__ = wrapper.__doc__
        wrapped.__name__ = wrapper.__name__
        return wrapped
