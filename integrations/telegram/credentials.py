import os
import httpx

SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY")
SYSTEM_API_ENDPOINT = os.getenv("SYSTEM_API_ENDPOINT")


async def get_credentials_from_django(telegram_user_id: int) -> dict:
    """Fetch credentials from Django based on Telegram user ID."""
    url = f"{SYSTEM_API_ENDPOINT}/integrations/credentials/"
    headers = {
        "Authorization": f"Api-Key {SYSTEM_API_KEY}",
        "Content-Type": "application/json",
    }
    data = '{"key_value": "' + str(telegram_user_id) + '"}'
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request("GET", url, headers=headers, content=data)
            if response.status_code == 200:
                return response.json()
            return {"error": f"Status: {response.status_code}", "detail": response.text}
        except Exception as e:
            return {"error": str(e)}


def validate_credentials(credentials: dict) -> tuple[bool, str]:
    """
    Validate credentials and return (is_valid, error_message).
    """
    if not credentials or credentials.get("count", 0) == 0:
        return False, "not_eligible"
    
    if credentials.get("count", 0) > 1:
        return False, "duplicate"
    
    return True, ""
