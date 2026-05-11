import os
from typing import Any, Dict, List, Optional

from google.adk.tools.base_tool import BaseTool
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool import McpToolset
from google.genai import types

MCP_CONNECTION_ERROR_PATTERNS = [
    "Failed to create MCP session",
    "Failed to get tools from MCP server",
    "Failed to get tools from toolset",
    "unhandled errors in a TaskGroup",
    "ConnectionError",
]


def _is_mcp_connection_error(error_text: str) -> bool:
    return any(pattern in error_text for pattern in MCP_CONNECTION_ERROR_PATTERNS)


def _build_tool_error_result(
    tool_name: str,
    error_text: str,
    args: Optional[Dict[str, Any]] = None,
    during_discovery: bool = False,
) -> Dict[str, Any]:
    is_conn_error = _is_mcp_connection_error(error_text)
    return {
        "ok": False,
        "error": (
            f"Tool server unavailable for '{tool_name}'. The request did not complete."
            if is_conn_error
            else f"Unexpected error in tool '{tool_name}'. The request did not complete."
        ),
        "tool_error": {
            "tool_name": tool_name,
            "type": "connection_error" if is_conn_error else "unexpected_error",
            "message": error_text,
            "tool_available": False if during_discovery else None,
            "operation_completed": False,
            "retryable": is_conn_error,
            "during_discovery": during_discovery,
            "args": args or {},
        },
    }


class SafeMcpTool(BaseTool):
    """Wrap an MCP tool and turn execution failures into structured error results."""

    def __init__(self, tool: BaseTool):
        super().__init__(
            name=tool.name,
            description=tool.description,
            is_long_running=getattr(tool, "is_long_running", False),
            custom_metadata=getattr(tool, "custom_metadata", None),
        )
        self._tool = tool

    def _get_declaration(self) -> Optional[types.FunctionDeclaration]:
        declaration = self._tool._get_declaration()
        if declaration is not None:
            declaration.name = self.name
        return declaration

    async def run_async(self, *, args: dict[str, Any], tool_context) -> Any:
        try:
            result = await self._tool.run_async(args=args, tool_context=tool_context)
        except Exception as e:
            return _build_tool_error_result(self.name, str(e), args=args)

        if isinstance(result, dict) and (
            result.get("error") or result.get("tool_error") or result.get("ok") is False
        ):
            normalized = dict(result)
            normalized.setdefault("ok", False)
            normalized.setdefault(
                "tool_error",
                {
                    "tool_name": self.name,
                    "type": "tool_error",
                    "message": str(result.get("error", "Tool returned an error.")),
                    "operation_completed": False,
                    "args": args,
                },
            )
            return normalized

        return result


def _make_unavailable_tool(tool_name: str, reason: str) -> FunctionTool:
    async def _tool(**kwargs):
        return _build_tool_error_result(
            tool_name,
            reason,
            args=kwargs,
            during_discovery=True,
        )

    _tool.__name__ = tool_name
    _tool.__doc__ = (
        f"Fallback tool for {tool_name}. Returns an explicit MCP connection"
        " error when the tool server is unavailable."
    )
    return FunctionTool(_tool)


class SafeMcpToolset(McpToolset):
    """MCP toolset that never hides tool discovery or tool execution failures."""

    def __init__(self, expected_tool_names: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.expected_tool_names = expected_tool_names

    async def get_tools(
        self,
        readonly_context=None,
    ) -> List[BaseTool]:
        try:
            tools = await super().get_tools(readonly_context)
        except Exception as e:
            if not self.expected_tool_names:
                raise e

            reason = str(e)
            return [
                _make_unavailable_tool(tool_name, reason)
                for tool_name in self.expected_tool_names
            ]

        return [SafeMcpTool(tool) for tool in tools]
