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
from mutagen.mp3 import MP3

from .utils import download, poll_until_ready

log = get_logger("audio_gen")

MAX_DURATION = 30  # seconds — truncate audio to this length

# MPEG1 Layer 3 bitrate lookup (index → kbps)
_BITRATES = {
    0x01: 32, 0x02: 40, 0x03: 48, 0x04: 56, 0x05: 64,
    0x06: 80, 0x07: 96, 0x08: 112, 0x09: 128, 0x0a: 160,
    0x0b: 192, 0x0c: 224, 0x0d: 256, 0x0e: 320,
}
_SAMPLE_RATES = {0x00: 44100, 0x01: 48000, 0x02: 32000}


def _find_truncation_point(raw: bytes, target_seconds: float) -> int:
    """Walk MP3 frames and return the byte offset after target_seconds."""
    pos = 0
    # Skip ID3v2 tag if present
    if raw[:3] == b"ID3":
        size = (
            ((raw[6] & 0x7F) << 21)
            | ((raw[7] & 0x7F) << 14)
            | ((raw[8] & 0x7F) << 7)
            | (raw[9] & 0x7F)
        )
        pos = size + 10

    elapsed = 0.0
    while pos < len(raw) - 4 and elapsed < target_seconds:
        header = (raw[pos] << 24) | (raw[pos + 1] << 16) | (raw[pos + 2] << 8) | raw[pos + 3]
        if (header >> 21) & 0x7FF != 0x7FF:
            pos += 1
            continue

        br_idx = (header >> 12) & 0x0F
        sr_idx = (header >> 10) & 0x03
        padding = (header >> 9) & 0x01

        bitrate = _BITRATES.get(br_idx)
        sample_rate = _SAMPLE_RATES.get(sr_idx)
        if not bitrate or not sample_rate:
            pos += 1
            continue

        frame_size = (144 * bitrate * 1000 // sample_rate) + padding
        elapsed += 1152.0 / sample_rate
        pos += frame_size

    return pos

POLL_INTERVAL = 20  # seconds between status checks
MAX_POLL_ATTEMPTS = 90  # ~30 minutes max wait


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

    # Truncate to MAX_DURATION seconds using frame-accurate MP3 parsing
    info = MP3(str(output_path)).info
    if info.length > MAX_DURATION:
        log.info("Truncating audio from %.1fs to %ds", info.length, MAX_DURATION)
        raw = output_path.read_bytes()
        pos = _find_truncation_point(raw, MAX_DURATION)
        output_path.write_bytes(raw[:pos])
        log.info("Truncated audio to %d bytes (%.0f KB)", pos, pos / 1024)

    log.info("Audio saved to %s", output_path)
    return str(output_path), audio_url
