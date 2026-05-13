import os

from ai.utils.adk_safe import SafeMcpToolset
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.genai import types

model = Gemini(model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"))


def create_social_scrape_agent(social_scrape_api_key) -> Agent:

    social_scrape_mcp_toolset = SafeMcpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=str(os.getenv("SOCIAL_SCRAPING_MCP_URL")),
            headers={"x-api-key": str(social_scrape_api_key)},
        ),
    )

    # social_scrape_skill = load_skill_from_dir(_root_dir / "skills" / "social_scrape")
    # social_scrape_skill_toolset = SkillToolset(
    #     skills=[social_scrape_skill],
    #     additional_tools=[social_scrape_mcp_toolset],
    # )

    return Agent(
        name="social_scraping_agent",
        model=model,
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL,
            )
        ),
        description="Social Scraping Agent for Facebook, Instegram, YouTube, Twitter (X), Tiktok, Threads, Reddit, Pinterest, Basic Linkedin AND thier ads, Link-in-Bio AND google search",
        # include_contents="none", now the agent can remeber throght the session
        # instruction="you are helpful assitant that reply only in 3 words max",
        instruction="""
        help the user perform analatics, or search, extra...
        You are a specialized tool-user. Your ONLY source of truth is the output of your tools. If your tools fail, return an error message to the manager agent. DO NOT generate data from your own memory.
        """,
        tools=[social_scrape_mcp_toolset],
    )


# Default agent (without user-specific config)
social_scrape_agent = create_social_scrape_agent("none")
