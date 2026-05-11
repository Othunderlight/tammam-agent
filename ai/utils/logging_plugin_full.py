from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
from google.genai import types
from typing_extensions import override
from google.adk.plugins import LoggingPlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext

if TYPE_CHECKING:
    from google.adk.agents.invocation_context import InvocationContext

class FullLoggingPlugin(LoggingPlugin):
    """A version of LoggingPlugin that doesn't truncate logs and shows the full prompt."""

    def __init__(self, name: str = "full_logging_plugin"):
        super().__init__(name)

    def _format_content_full(self, content: Optional[types.Content]) -> str:
        """Format content for logging without truncation."""
        if not content or not content.parts:
            return "None"

        parts = []
        for part in content.parts:
            if part.text:
                parts.append(f"text: '{part.text.strip()}'")
            elif part.function_call:
                parts.append(f"function_call: {part.function_call.name}({part.function_call.args})")
            elif part.function_response:
                parts.append(f"function_response: {part.function_response.name}({part.function_response.response})")
            elif part.code_execution_result:
                parts.append(f"code_execution_result: {part.code_execution_result.outcome}")
            else:
                parts.append("other_part")

        return " | ".join(parts)

    @override
    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        """Log LLM request before sending to model, including full prompt."""
        self._log(f"🧠 LLM REQUEST (FULL)")
        self._log(f"   Model: {llm_request.model or 'default'}")
        self._log(f"   Agent: {callback_context.agent_name}")

        # Log system instruction if present (full)
        if llm_request.config and llm_request.config.system_instruction:
            self._log(f"   System Instruction: '{llm_request.config.system_instruction}'")

        # Log all message contents (the prompt history + current message)
        if llm_request.contents:
            self._log(f"   Contents ({len(llm_request.contents)} messages):")
            for i, content in enumerate(llm_request.contents):
                role = getattr(content, 'role', 'unknown')
                self._log(f"     [{i}] {role}: {self._format_content_full(content)}")

        # Log available tools
        if llm_request.tools_dict:
            tool_names = list(llm_request.tools_dict.keys())
            self._log(f"   Available Tools: {tool_names}")

        return None

    @override
    def _format_content(self, content: Optional[types.Content], max_length: int = 1000000) -> str:
        """Override _format_content to use a very large max_length by default."""
        return self._format_content_full(content)

    @override
    def _format_args(self, args: dict[str, Any], max_length: int = 1000000) -> str:
        """Override _format_args to use a very large max_length by default."""
        if not args:
            return "{}"
        return str(args)
