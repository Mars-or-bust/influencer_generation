"""
Step 3 — Generate a lip-synced avatar video using Segmind Infinite Talk.

Takes a public image URL and audio URL, submits to Segmind's
infinite-talk endpoint, and saves the resulting video.
"""

from __future__ import annotations

import requests

from .config import (
    OUTPUT_DIR,
    AVATAR_IMAGE_URL,
    SEGMIND_API_KEY,
    SEGMIND_BASE_URL,
    get_logger,
)
from .utils import download, poll_until_ready

log = get_logger("video_gen")

POLL_INTERVAL = 15  # seconds
MAX_POLL_ATTEMPTS = 80  # ~20 minutes


def _headers() -> dict:
    return {
        "x-api-key": SEGMIND_API_KEY,
        "Content-Type": "application/json",
    }


def _try_extract_url(result: dict) -> str | None:
    """Try to extract a video URL from a JSON response."""
    for key in ("output_url", "output", "video_url", "video", "url", "result"):
        if key in result and isinstance(result[key], str) and result[key].startswith("http"):
            return result[key]
    return None


def _extract_video_result(data: dict) -> str | None:
    """Extract video URL from poll response, raise on failure."""
    status = data.get("status", "")
    if status == "FAILED":
        raise RuntimeError(f"Segmind video generation failed: {data}")
    if status == "COMPLETED":
        for key in ("output_url", "output", "video_url", "url"):
            if key in data and isinstance(data[key], str):
                return data[key]
    return None


def generate_video(
    audio_url: str,
    video_prompt: str,
    image_url: str | None = None,
    seed: int = 42424242,
    resolution: str = "480p",
    fps: int = 16,
) -> str:
    """Generate a lip-synced avatar video via Segmind Infinite Talk.

    Args:
        audio_url: Public URL to the audio file.
        video_prompt: Scene/emotion description for the avatar.
        image_url: Public URL of the avatar image.
                   Falls back to AVATAR_IMAGE_URL from .env.
        seed: Random seed for reproducibility.
        resolution: Video resolution (e.g. "480p").
        fps: Frames per second.

    Returns:
        Path to the downloaded video file.
    """
    if not SEGMIND_API_KEY:
        raise RuntimeError("SEGMIND_API_KEY not set in .env")

    image = image_url or AVATAR_IMAGE_URL
    if not image:
        raise RuntimeError(
            "No avatar image URL provided. Set AVATAR_IMAGE_URL in .env "
            "or pass image_url."
        )

    log.info("Submitting video generation to Segmind / Infinite Talk")

    payload = {
        "image": image,
        "audio": audio_url,
        "prompt": video_prompt,
        "seed": seed,
        "resolution": resolution,
        "fps": fps,
    }

    url = f"{SEGMIND_BASE_URL}/v1/infinite-talk"
    response = requests.post(url, headers=_headers(), json=payload, timeout=60)

    output_path = OUTPUT_DIR / "video.mp4"
    content_type = response.headers.get("Content-Type", "")

    if "application/json" in content_type or "text/" in content_type:
        # JSON response — may contain a URL or poll info
        body = response.json()
        log.info("Segmind JSON response keys: %s", list(body.keys()))
        response.raise_for_status()

        video_url = _try_extract_url(body)
        if not video_url:
            # Async — poll for completion
            poll_url = body.get("poll_url") or body.get("status_url")
            if not poll_url:
                raise RuntimeError(f"Unexpected Segmind response: {body}")

            video_url = poll_until_ready(
                url=poll_url,
                headers=_headers(),
                extract_fn=_extract_video_result,
                interval=POLL_INTERVAL,
                max_attempts=MAX_POLL_ATTEMPTS,
                logger=log,
            )

        download(video_url, output_path)
    else:
        # Binary response — the body IS the video
        response.raise_for_status()
        output_path.write_bytes(response.content)

    size_kb = output_path.stat().st_size / 1024
    log.info("Video saved to %s (%.0f KB)", output_path, size_kb)
    return str(output_path)
