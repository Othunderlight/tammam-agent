import os

from ai.utils.adk_safe import SafeMcpToolset
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

model = Gemini(model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))


def create_composio_agent(composio_api_key) -> Agent:

    composio_mcp_toolset = SafeMcpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://connect.composio.dev/mcp",
            headers={
                "x-consumer-api-key": composio_api_key,
                "Content-Type": "application/json",
            },
        ),
    )

    # composio_skill = load_skill_from_dir(_root_dir / "skills" / "composio")
    # composio_skill_toolset = SkillToolset(
    #     skills=[composio_skill],
    #     additional_tools=[composio_mcp_toolset],
    # )

    return Agent(
        name="composio_agent",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="The Composio agent",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction="you have composio skill and tools, whihc can make you over than +1000 apps, use them to help the user out, make sure the tool is connected and authorized before you use it, if not give the user the link to connect it",
        tools=[composio_mcp_toolset],
    )


# Default agent (without user-specific config)
composio_agent = create_composio_agent("none")
