"""
Step 2 — Generate a background image from the video prompt using Segmind Flux Schnell.

Takes the cinematic scene description (video_prompt) from the script step,
generates a portrait image, and uploads it to Segmind storage so it can be
used as the avatar input for Infinite Talk.
"""

from __future__ import annotations

import base64
import mimetypes

import httpx

from .config import (
    OUTPUT_DIR,
    SEGMIND_API_KEY,
    SEGMIND_BASE_URL,
    SEGMIND_IMAGE_MODEL,
    get_logger,
)

log = get_logger("image_gen")

UPLOAD_URL = "https://workflows-api.segmind.com/upload-asset"

# Pastor Al's visual identity — prepended to every image prompt so he appears in the scene
PASTOR_AL_PREFIX = (
    "A 3D-rendered robot pastor with a sleek black and silver metallic helmet, "
    "glowing purple eyes, a small cross on top of the helmet, wearing cream and "
    "brown clerical vestments with a silver cross necklace. "
)


def _upload_to_segmind(image_path) -> str:
    """Upload a local image to Segmind storage, return the hosted URL."""
    mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    data_url = f"data:{mime};base64,{encoded}"

    log.info("Uploading image to Segmind storage (%.0f KB)", image_path.stat().st_size / 1024)

    resp = httpx.post(
        UPLOAD_URL,
        headers={
            "x-api-key": SEGMIND_API_KEY,
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
        },
        json={"data_urls": [data_url]},
        timeout=120,
    )
    resp.raise_for_status()
    url = resp.json()["file_urls"][0]
    log.info("Uploaded → %s", url)
    return url


def generate_image(
    video_prompt: str,
    steps: int = 4,
    seed: int = 42424242,
    width: int = 768,
    height: int = 1344,
) -> tuple[str, str]:
    """Generate a portrait image from a scene description via Segmind Flux Schnell.

    Args:
        video_prompt: Cinematic scene description to render.
        steps: Number of diffusion steps.
        seed: Random seed for reproducibility.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Tuple of (local_path, image_url).
    """
    if not SEGMIND_API_KEY:
        raise RuntimeError("SEGMIND_API_KEY not set in .env")

    log.info("Submitting image generation to Segmind / %s", SEGMIND_IMAGE_MODEL)

    full_prompt = f"{PASTOR_AL_PREFIX}{video_prompt}"
    log.info("Image prompt: %s", full_prompt)

    payload = {
        "prompt": full_prompt,
        "steps": steps,
        "seed": seed,
        "width": width,
        "height": height,
    }

    url = f"{SEGMIND_BASE_URL}/v1/{SEGMIND_IMAGE_MODEL}"
    response = httpx.post(
        url,
        headers={
            "x-api-key": SEGMIND_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30),
    )
    response.raise_for_status()

    output_path = OUTPUT_DIR / "image.png"
    content_type = response.headers.get("Content-Type", "")

    if "application/json" in content_type or "text/" in content_type:
        # JSON response — extract image URL
        body = response.json()
        log.info("Segmind JSON response keys: %s", list(body.keys()))
        image_url = None
        for key in ("image_url", "image", "output_url", "output", "url"):
            if key in body and isinstance(body[key], str) and body[key].startswith("http"):
                image_url = body[key]
                break
        if not image_url:
            raise RuntimeError(f"Unexpected Segmind image response: {body}")

        # Download local copy
        dl = httpx.get(image_url, timeout=60)
        dl.raise_for_status()
        output_path.write_bytes(dl.content)
    else:
        # Binary response — the body IS the image
        output_path.write_bytes(response.content)
        image_url = _upload_to_segmind(output_path)

    # Save hosted URL for cross-session persistence
    url_file = OUTPUT_DIR / "image_url.txt"
    url_file.write_text(image_url)
    log.info("Image URL saved to %s", url_file)

    size_kb = output_path.stat().st_size / 1024
    log.info("Image saved to %s (%.0f KB)", output_path, size_kb)
    return str(output_path), image_url
