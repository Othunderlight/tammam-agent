import os

import httpx
import inngest
from auth import generate_system_token
from services.django_actions import (
    fetch_django_context,
    fetch_org_knowledge_base,
    update_django_record,
    bulk_create_activities,
)
from services.llm import generate_recommendation
from services.conversation_parser import parse_conversation
from services.email_service import send_email_task

# Create an Inngest client
inngest_client = inngest.Inngest(
    app_id="fastapi_founderstack",
)

DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://localhost:8000/api")


# Create a simple test function
@inngest_client.create_function(
    fn_id="hello_world",
    trigger=inngest.TriggerEvent(event="test/hello.world"),
)
async def hello_world(ctx: inngest.Context) -> dict:
    return {
        "message": "Hello from Inngest!",
        "event_name": ctx.event.name,
        "data": ctx.event.data,
    }


@inngest_client.create_function(
    fn_id="handle_activity_log",
    trigger=inngest.TriggerEvent(event="activity/log.created"),
)
async def handle_activity_log(ctx: inngest.Context) -> dict:
    """
    Triggered when a new activity log is created.
    1. Fetch full context for the related person.
    2. Call Gemini to get a recommendation.
    3. Update the related records in Django.
    """
    event_data = ctx.event.data
    person_id = event_data.get("person_id")

    if not person_id:
        ctx.logger.info("No person_id found in activity log, skipping recommendation.")
        return {"status": "skipped", "reason": "no_person_id"}

    ctx.logger.info(f"Processing activity log for person: {person_id}")

    system_token = generate_system_token()
    headers = {"Authorization": f"Bearer {system_token}"}

    # Define URLs
    context_url = (
        f"{DJANGO_API_URL}/people/{person_id}/context/?sections=general,context"
    )
    update_url = f"{DJANGO_API_URL}/people/{person_id}/"

    async with httpx.AsyncClient() as client:
        # Step 1: Fetch context from Django
        try:
            context_data = await fetch_django_context(
                client, context_url, headers, logger=ctx.logger
            )
        except Exception as e:
            return {"status": "error", "detail": f"fetch_context_failed: {str(e)}"}

        # Step 2: Fetch Organization Files
        org_id = context_data.get("organization")
        knowledge_base = ""
        if org_id:
            files_url = f"{DJANGO_API_URL}/files/for-org/{org_id}/"
            knowledge_base = await fetch_org_knowledge_base(
                client, files_url, headers, logger=ctx.logger
            )

        # Step 3: Call the AI
        try:
            recommendation = await generate_recommendation(context_data, knowledge_base)
            ctx.logger.info(f"Generated recommendation: {recommendation}")
        except Exception as e:
            ctx.logger.error(f"AI Recommendation failed: {e}")
            return {"status": "error", "detail": f"ai_failed: {str(e)}"}

        # Step 4: Update the related records in Django
        try:
            await update_django_record(
                client,
                update_url,
                {"recommended_action": f"AI: {recommendation}"},
                headers,
                logger=ctx.logger,
            )
        except Exception as e:
            return {"status": "error", "detail": f"update_django_failed: {str(e)}"}

    return {
        "status": "success",
        "person_id": person_id,
        "recommendation": recommendation,
    }


@inngest_client.create_function(
    fn_id="parse_conversation",
    trigger=inngest.TriggerEvent(event="conversation/parse.requested"),
)
async def parse_conversation_handler(ctx: inngest.Context) -> dict:
    """
    Triggered when user pastes a conversation to parse.
    1. Call Gemini to parse conversation into activities.
    2. Bulk create activities in Django.
    """
    event_data = ctx.event.data
    person_id = event_data.get("person_id")
    conversation_text = event_data.get("conversation_text")
    person_name = event_data.get("person_name", "Contact")
    channel_hint = event_data.get("channel_hint")
    user_id = event_data.get("user_id")  # Get the actual user who triggered this

    if not person_id:
        ctx.logger.error("No person_id provided")
        return {"status": "error", "reason": "no_person_id"}

    if not conversation_text:
        ctx.logger.error("No conversation_text provided")
        return {"status": "error", "reason": "no_conversation_text"}

    ctx.logger.info(f"Parsing conversation for person: {person_id}, triggered by user: {user_id}")

    # Step 1: Parse conversation with AI
    try:
        parsed = await parse_conversation(
            conversation_text=conversation_text,
            person_name=person_name,
            channel_hint=channel_hint
        )
        activities = [activity.model_dump() for activity in parsed.activities]
        ctx.logger.info(f"Parsed {len(activities)} activities from conversation")
    except Exception as e:
        ctx.logger.error(f"AI Parsing failed: {e}")
        return {"status": "error", "detail": f"ai_parsing_failed: {str(e)}"}

    if not activities:
        ctx.logger.info("No activities parsed from conversation")
        return {"status": "success", "activities_created": 0}

    # Step 2: Bulk create activities in Django (using the actual user's token)
    system_token = generate_system_token(user_id=user_id)
    headers = {"Authorization": f"Bearer {system_token}"}

    async with httpx.AsyncClient() as client:
        try:
            result = await bulk_create_activities(
                client,
                activities=activities,
                person_id=person_id,
                headers=headers,
                logger=ctx.logger
            )
            ctx.logger.info(f"Created {len(result)} activities in Django")
        except Exception as e:
            ctx.logger.error(f"Failed to create activities in Django: {e}")
            return {"status": "error", "detail": f"django_create_failed: {str(e)}"}

    return {
        "status": "success",
        "person_id": person_id,
        "activities_created": len(activities),
    }

@inngest_client.create_function(
    fn_id="send_email",
    trigger=inngest.TriggerEvent(event="email/send.requested"),
)
async def send_email_handler(ctx: inngest.Context) -> dict:
    return await send_email_task(ctx)


# Export functions for serving
inngest_functions = [
    hello_world,
    handle_activity_log,
    parse_conversation_handler,
    send_email_handler,
]
