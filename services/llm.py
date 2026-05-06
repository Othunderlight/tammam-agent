import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from helpers.toon import to_toon

# Load env from the specific path if needed, but usually it's already loaded in main.py
env_path = "/home/omar/Desktop/FounderStackCRM/fastai/.env"
load_dotenv(dotenv_path=env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# client = genai.Client(api_key=GEMINI_API_KEY)


def _log_prompt(prompt: str):
    print("\n--- DEBUG: FINAL PROMPT SENT TO AI ---")
    print(prompt)
    print("--- END OF DEBUG PROMPT ---\n")


async def generate_recommendation(context_data: dict, knowledge_base: str = "") -> str:
    """
    Generates a next action recommendation based on lead context and organizational knowledge.
    """
    return None
    # Convert context_data to TOON for token efficiency
    toon_context = to_toon(context_data)

    prompt = f"""
    Analyze the following lead history and status, taking into account the organizational knowledge provided.
    Return ONE short actionable sentence (max 15 words) for the next step.

    Organizational Knowledge:
    {knowledge_base if knowledge_base else "No specific organizational knowledge provided."}

    Lead Context (TOON format):
    {toon_context}

    Actionable Recommendation:
    """

    _log_prompt(prompt)  # Uncomment this line to see the final prompt in the terminal

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            system_instruction="You are a sales assistant helping a founder manage their CRM. Your goal is to provide a single, clear, and highly actionable next step for a lead. Use a direct tone. Example: 'Follow up in 3 days via email', 'Mark as Lost - no response', 'Send pricing deck now'.",
        ),
        contents=prompt,
    )

    return response.text.strip()
