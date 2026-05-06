"""
Conversation Parser Service

Parses raw conversation text into structured ActivityLog entries using Gemini.
"""

import os
from datetime import datetime
from typing import List, Literal, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Load environment
env_path = "/home/omar/Desktop/FounderStackCRM/fastai/.env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================================
# Pydantic Models for Structured Output
# ============================================================================


class ParsedActivity(BaseModel):
    """A single parsed activity/message from the conversation."""

    type: Literal[
        "note", "email", "call", "meeting", "linkedin_msg", "whatsapp_msg"
    ] = Field(
        description="Type of activity. Use 'linkedin_msg' for LinkedIn, 'whatsapp_msg' for WhatsApp, 'email' for emails, 'note' for general notes."
    )
    channel: Optional[Literal["email", "linkedin", "whatsapp", "system"]] = Field(
        default=None,
        description="Communication channel. Should match type: linkedin_msg->linkedin, whatsapp_msg->whatsapp, email->email",
    )
    direction: Literal["received", "sent"] = Field(
        description="'sent' if you/the user sent this message, 'received' if the other person sent it"
    )
    title: Optional[str] = Field(
        default=None,
        description="Brief title/subject (max 50 chars). Optional for messages.",
    )
    content: str = Field(description="The actual message content")
    date: str = Field(
        description="ISO format datetime (YYYY-MM-DDTHH:MM:SS). Use today's date if not specified, with logical time ordering."
    )


class ParsedConversation(BaseModel):
    """Container for all parsed activities from a conversation."""

    activities: List[ParsedActivity] = Field(
        description="List of parsed messages/activities in chronological order"
    )


# ============================================================================
# Parser Function
# ============================================================================

SYSTEM_PROMPT = """You are a CRM conversation parser. Your job is to extract structured activity logs from raw conversation text.

RULES:
1. Parse EVERY message in the conversation into a separate activity
2. Identify the direction: "sent" = user/founder wrote it, "received" = the lead/contact wrote it
3. Infer the channel from context clues (LinkedIn, WhatsApp, Email, etc.)
4. If no time is specified, use today's date with logical timestamps (start at 09:00, increment by 15 mins)
5. Keep content exactly as written, do not summarize
6. Set appropriate channel based on type (linkedin_msg -> linkedin, whatsapp_msg -> whatsapp, etc.)

EXAMPLES OF DIRECTION DETECTION:
- "Me:", "I:", "[You]", "[Sent]", "→" = direction: "sent"
- Names like "John:", "[John]", "<Person Name>:" = direction: "received"
- Reply indicators, quoted text = analyze context

OUTPUT: Return a JSON with 'activities' array containing each parsed message."""


async def parse_conversation(
    conversation_text: str,
    person_name: str = "Contact",
    channel_hint: Optional[str] = None,
):
    """
    Parse raw conversation text into structured ActivityLog entries.

    Args:
        conversation_text: Raw pasted conversation
        person_name: Name of the person/lead (helps AI identify direction)
        channel_hint: Optional hint about the channel (linkedin, whatsapp, email)

    Returns:
        ParsedConversation with list of activities
    """
    return None
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""Parse this conversation into structured activity logs.

The conversation is with: {person_name}
Today's date: {today}
{f"Channel hint: {channel_hint}" if channel_hint else "Infer the channel from context"}

CONVERSATION:
---
{conversation_text}
---

Parse each message into an activity. Return JSON matching the schema."""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ParsedConversation,
        ),
    )

    # Parse and validate response
    parsed = ParsedConversation.model_validate_json(response.text)
    return parsed


async def parse_conversation_sync(
    conversation_text: str,
    person_name: str = "Contact",
    channel_hint: Optional[str] = None,
) -> dict:
    """
    Synchronous wrapper that returns dict for API responses.
    """
    result = await parse_conversation(conversation_text, person_name, channel_hint)
    return result.model_dump()
