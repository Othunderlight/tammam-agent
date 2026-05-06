import base64
import os
from typing import Optional

import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3")


def _is_valid_transcript(text: Optional[str]) -> bool:
    """Return True when the STT result looks usable."""
    if not text:
        return False

    normalized = text.strip().lower()
    if not normalized:
        return False

    invalid_markers = {
        "audio msg parsing error",
        "ask the user to try again or use text directly.",
    }
    return normalized not in invalid_markers


async def _resolve_audio_data(
    url: Optional[str], audio_data: Optional[bytes]
) -> Optional[bytes]:
    """Resolve audio bytes from either inline data or a remote URL."""
    if audio_data is not None:
        return audio_data

    if not url:
        print("STT skipped: neither audio_data nor url was provided.")
        return None

    try:
        async with httpx.AsyncClient() as client:
            audio_response = await client.get(url)
            if audio_response.status_code != 200:
                print(
                    f"STT failed to download audio. status={audio_response.status_code}"
                )
                return None
            return audio_response.content
    except Exception as e:
        print(f"STT audio download exception. error={e}")
        return None


async def transcribe_audio(
    mime_type: str,
    model: str,
    url: Optional[str] = None,
    audio_data: Optional[bytes] = None,
) -> Optional[str]:
    """Transcribe audio using Gemini or Groq Whisper."""
    resolved_audio = await _resolve_audio_data(url=url, audio_data=audio_data)
    if resolved_audio is None:
        return None

    if model in {"groq", "whisper-large-v3", "whisper-large-v3-turbo"}:
        return await _transcribe_groq(resolved_audio, mime_type, model)

    try:
        result = await _transcribe_gemini(resolved_audio, mime_type, model)
        if _is_valid_transcript(result):
            return result
        print(
            f"Gemini STT returned unusable output. model={model} "
            f"result={(result or '')[:200]}"
        )
    except Exception as e:
        print(f"Gemini STT bubbled exception. model={model} error={e}")

    if GROQ_API_KEY:
        print(f"Falling back to Groq STT. model={GROQ_STT_MODEL}")
        return await _transcribe_groq(resolved_audio, mime_type, GROQ_STT_MODEL)

    return None


async def _transcribe_gemini(
    audio_data: bytes, mime_type: str, model: str
) -> Optional[str]:
    """Transcribe audio using Google's Gemini API."""
    if not GEMINI_API_KEY:
        print("Gemini STT skipped: GEMINI_API_KEY is not set.")
        return None

    try:
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        api_url = f"https://aiplatform.googleapis.com/v1beta1/projects/founderstack-491517/locations/global/publishers/google/models/{model}:generateContent?key={GEMINI_API_KEY}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": "Transcribe this audio clip"},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": audio_base64,
                            }
                        },
                    ],
                }
            ],
            "system_instruction": {
                "parts": [
                    {
                        "text": "Your ONLY CAUSE is to transcribe the audio, if you could not do that for whatever reason say: audio msg parsing error, ask the user to try again or use text directly."
                    }
                ]
            },
            "generationConfig": {"thinkingConfig": {"thinkingBudget": 0}},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("candidates"):
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            print(
                f"Gemini STT request failed. model={model} status={response.status_code} body={response.text[:500]}"
            )
    except Exception as e:
        print(f"Gemini STT exception. model={model} error={e}")
    return None


async def _transcribe_groq(
    audio_data: bytes, mime_type: str, model: str
) -> Optional[str]:
    """Transcribe audio using Groq Whisper."""
    if not GROQ_API_KEY:
        print("Groq STT skipped: GROQ_API_KEY is not set.")
        return None

    try:
        extension = mime_type.split("/")[-1] if "/" in mime_type else "ogg"
        groq_url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        files = {
            "file": (
                f"audio.{extension}",
                audio_data,
                mime_type,
            )
        }
        data = {"model": model}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                groq_url,
                headers=headers,
                files=files,
                data=data,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("text"):
                    return data["text"]
            print(
                f"Groq STT request failed. model={model} status={response.status_code} body={response.text[:500]}"
            )
    except Exception as e:
        print(f"Groq STT exception. model={model} error={e}")
    return None
