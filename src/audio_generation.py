"""
Step 2 — Generate spoken-word audio using MusicAPI.ai (Sonic model).

Takes the script text as lyrics and an audio style description, submits to
MusicAPI, polls until generation completes, and downloads the resulting audio.
"""

from __future__ import annotations

import httpx

from .config import (
    OUTPUT_DIR,
    MUSICAPI_API_KEY,
    MUSICAPI_BASE_URL,
    MUSICAPI_MODEL,
    get_logger,
)
from .utils import download, poll_until_ready

log = get_logger("audio_gen")

POLL_INTERVAL = 20  # seconds between status checks
MAX_POLL_ATTEMPTS = 40  # ~13 minutes max wait


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {MUSICAPI_API_KEY}",
        "Content-Type": "application/json",
    }


def _extract_audio_url(body: dict) -> str | None:
    """Extract audio URL from MusicAPI task poll response.

    Returns the URL when the task has succeeded, None if still processing.
    Raises on failure.
    """
    state = body.get("state")

    if state == "failed":
        raise RuntimeError(f"MusicAPI task failed: {body}")

    if state != "succeeded":
        return None

    data = body.get("data", {})

    # Handle both list and dict response shapes
    if isinstance(data, list) and data:
        url = data[0].get("audio_url")
        if url:
            return url
    elif isinstance(data, dict):
        url = data.get("audio_url")
        if url:
            return url

    return None


def generate_audio(
    script_text: str,
    audio_style: str,
    title: str = "AI Influencer Script",
) -> tuple[str, str]:
    """Generate a spoken-word audio track from the script.

    Args:
        script_text: The script text (used as lyrics).
        audio_style: Genre/style description for the track.
        title: Track title.

    Returns:
        Tuple of (local_path, audio_url).
    """
    if not MUSICAPI_API_KEY:
        raise RuntimeError("MUSICAPI_API_KEY not set in .env")

    log.info("Submitting audio generation to MusicAPI")

    payload = {
        "custom_mode": True,
        "mv": MUSICAPI_MODEL,
        "title": title,
        "tags": audio_style,
        "prompt": script_text,
    }

    with httpx.Client(base_url=MUSICAPI_BASE_URL, timeout=30) as client:
        resp = client.post("/api/v1/sonic/create", headers=_headers(), json=payload)
        resp.raise_for_status()
        task_id = resp.json()["task_id"]

    log.info("MusicAPI task created — task_id: %s", task_id)

    audio_url = poll_until_ready(
        url=f"{MUSICAPI_BASE_URL}/api/v1/sonic/task/{task_id}",
        headers=_headers(),
        extract_fn=_extract_audio_url,
        interval=POLL_INTERVAL,
        max_attempts=MAX_POLL_ATTEMPTS,
        logger=log,
    )

    # Save the hosted URL for cross-session persistence
    url_file = OUTPUT_DIR / "audio_url.txt"
    url_file.write_text(audio_url)
    log.info("Audio URL saved to %s", url_file)

    # Download a local copy
    output_path = OUTPUT_DIR / "audio.mp3"
    download(audio_url, output_path)

    log.info("Audio saved to %s", output_path)
    return str(output_path), audio_url
