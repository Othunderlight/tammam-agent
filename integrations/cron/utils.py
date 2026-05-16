import os
import httpx

SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY")
SYSTEM_API_ENDPOINT = os.getenv("SYSTEM_API_ENDPOINT")

async def update_cron_status(
    cron_id: int, 
    status: str, 
    error: str = None, 
    delivery_error: str = None
) -> bool:
    """Update the status of a CronJob in Django."""
    url = f"{SYSTEM_API_ENDPOINT}/cron/jobs/{cron_id}/update-status/"
    headers = {
        "Authorization": f"Api-Key {SYSTEM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "last_status": status,
        "last_error": error,
        "last_delivery_error": delivery_error,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.patch(url, headers=headers, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to update cron status for {cron_id}: {e}")
            return False

def can_run_cron(credentials: dict) -> bool:
    """Check if the user can run the cron job based on credits."""
    results = credentials.get("results", [])
    if not results:
        return False
    keys = {k["name"]: k["value"] for k in results[0].get("keys", [])}
    return keys.get("can_continue") == "1"
