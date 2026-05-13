from ai.runs.one_action import AgentRequest, ask_agent
from ai.tools.crm_config import get_crm_config
from ai.tools.manage_api_key import clear_api_key, set_api_key
from ai.tools.usr.prefrence import get_my_preferences


def extract_user_info(credentials: dict) -> dict:
    """
    Extract relevant user info from credentials response.
    Works with any integration (Telegram, Slack, etc.) that returns the same format.
    """
    results = credentials.get("results", [])
    if not results:
        return {}

    user_data = results[0]
    user = user_data.get("user", {})
    org = user.get("organization", {})
    keys = {k["name"]: k["value"] for k in user_data.get("keys", [])}

    # Combine user_id and email for better safety in production (e.g., 1+example+gmail+com)
    original_id = str(user.get("id"))
    email = user.get("email") or ""
    safe_email = email.replace("@", "+").replace(".", "+")
    combined_user_id = f"{original_id}+{safe_email}" if safe_email else original_id

    return {
        "user_id": combined_user_id,
        "email": email,
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "organization_id": org.get("id"),
        "organization_name": org.get("name"),
        "integration_keys": keys,
    }


async def handle_integration_message(
    user_message: str,
    credentials: dict,
    message_callback=None,
    session_id=None,
    stop_key=None,
) -> dict:
    """
    Unified function to handle messages from any integration.

    Args:
        user_message: The text message from the user
        credentials: The credentials dict from get_credentials_from_django (or similar)
        message_callback: Optional async callback function to receive messages in real-time

    Returns:
        dict with 'status' and 'answer' (or 'error')
    """
    user_info = extract_user_info(credentials)

    if not user_info.get("user_id"):
        return {"status": "error", "answer": "Invalid credentials"}

    crm_api_key = user_info.get("integration_keys", {}).get("crm_api_key")
    composio_api_key = user_info.get("integration_keys", {}).get("composio_api_key")
    social_scrape_api_key = user_info.get("integration_keys", {}).get(
        "social_scrape_api_key"
    )
    if not crm_api_key:
        return {
            "status": "error",
            "answer": f"CRM API key not found in credentials. Available keys: {list(user_info.get('integration_keys', {}).keys())}",
        }

    set_api_key(crm_api_key)

    try:
        # Fetch CRM config to render agent prompt
        try:
            crm_config = get_crm_config()
            if not isinstance(crm_config, dict):
                print(
                    f"Warning: crm_config is not dict: {type(crm_config)} - {crm_config}"
                )
                crm_config = {}
        except Exception as e:
            print(f"Error fetching CRM config: {e}")
            crm_config = {}

        try:
            preferences = get_my_preferences()
            if not isinstance(preferences, dict):
                print(
                    f"Warning: preferences is not dict: {type(preferences)} - {preferences}"
                )
                preferences = {}
        except Exception as e:
            print(f"Error fetching user preferences: {e}")
            preferences = {}

        request = AgentRequest(
            user_id=user_info["user_id"],
            query=user_message,
            crm_config=crm_config,
            user_preferences=preferences,
            session_id=session_id,  # Use provided session_id or None for new session
            stop_key=stop_key,
            api_keys={
                "mcp_crm_api_key": crm_api_key,
                "composio_api_key": composio_api_key,
                "social_scrape_api_key": social_scrape_api_key,
            },
        )

        result = await ask_agent(request, message_callback=message_callback)
        return result
    finally:
        clear_api_key()
