"""Shared utilities for the content generation pipeline."""

from __future__ import annotations

import time
from typing import Callable

import httpx


def download(url: str, dest) -> None:
    """Download a file from a URL."""
    with httpx.stream("GET", url, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)


def poll_until_ready(
    url: str,
    headers: dict,
    extract_fn: Callable[[dict], str | None],
    *,
    params: dict | None = None,
    interval: int = 15,
    max_attempts: int = 40,
    logger=None,
) -> str:
    """Poll a URL until extract_fn returns a non-None result.

    Args:
        url: The URL to poll.
        headers: Request headers.
        extract_fn: Receives response JSON, returns a result string when ready
                    or None to keep polling. Should raise on failure.
        params: Optional query parameters.
        interval: Seconds between polls.
        max_attempts: Maximum number of poll attempts.
        logger: Optional logger for status messages.

    Returns:
        The extracted result string.

    Raises:
        TimeoutError: If max_attempts is exceeded.
    """
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)

        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        result = extract_fn(data)
        if result is not None:
            if logger:
                logger.info("Ready after %d polls", attempt)
            return result

        if logger:
            logger.info("Poll %d/%d — not ready yet", attempt, max_attempts)

    raise TimeoutError(f"Not ready after {max_attempts} polls")
