"""
Step 2 — Generate spoken-word audio using the Suno API (via sunoapi.org).

Takes the script text as lyrics and an audio style description, submits to
Suno, polls until generation completes, and downloads the resulting audio.
"""

from __future__ import annotations

import httpx

from .config import (
    OUTPUT_DIR,
    SUNO_API_KEY,
    SUNO_BASE_URL,
    SUNO_MODEL,
    get_logger,
)
from .utils import download, poll_until_ready

log = get_logger("audio_gen")

POLL_INTERVAL = 30  # seconds between status checks
MAX_POLL_ATTEMPTS = 40  # ~20 minutes max wait


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json",
    }


def _extract_audio_url(body: dict) -> str | None:
    """Extract audio URL from Suno poll response."""
    records = body.get("data", [])
    if isinstance(records, list) and records:
        url = records[0].get("audio_url")
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
    if not SUNO_API_KEY:
        raise RuntimeError("SUNO_API_KEY not set in .env")

    log.info("Submitting audio generation to Suno")

    payload = {
        "customMode": True,
        "instrumental": False,
        "prompt": script_text,
        "style": audio_style,
        "title": title,
        "model": SUNO_MODEL,
        "negativeTags": "heavy metal, EDM, rap, autotune, screaming, fast tempo, aggressive",
    }

    with httpx.Client(base_url=SUNO_BASE_URL, timeout=30) as client:
        resp = client.post("/api/v1/generate", headers=_headers(), json=payload)
        resp.raise_for_status()
        task_id = resp.json()["data"]["taskId"]

    log.info("Suno task created — taskId: %s", task_id)

    audio_url = poll_until_ready(
        url=f"{SUNO_BASE_URL}/api/v1/generate/record-info",
        headers=_headers(),
        extract_fn=_extract_audio_url,
        params={"taskId": task_id},
        interval=POLL_INTERVAL,
        max_attempts=MAX_POLL_ATTEMPTS,
        logger=log,
    )

    # Save the hosted URL for cross-session persistence
    url_file = OUTPUT_DIR / "suno_audio_url.txt"
    url_file.write_text(audio_url)
    log.info("Suno audio URL saved to %s", url_file)

    # Download a local copy
    output_path = OUTPUT_DIR / "audio.mp3"
    download(audio_url, output_path)

    log.info("Audio saved to %s", output_path)
    return str(output_path), audio_url
