"""Upload local resource files to Segmind storage and print the URLs."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes

import httpx

from config import RESOURCES_DIR, SEGMIND_API_KEY, get_logger

log = get_logger("upload")

UPLOAD_URL = "https://workflows-api.segmind.com/upload-asset"
METADATA_FILE = RESOURCES_DIR / ".upload_metadata.json"


MIME_OVERRIDES = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


def _file_hash(path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_metadata() -> dict:
    """Load the upload metadata file, or return an empty dict."""
    if METADATA_FILE.exists():
        return json.loads(METADATA_FILE.read_text())
    return {}


def _save_metadata(metadata: dict) -> None:
    """Persist upload metadata to disk."""
    METADATA_FILE.write_text(json.dumps(metadata, indent=2))


def upload_file(path) -> str:
    """Upload a single file to Segmind storage, return the hosted URL."""
    mime = MIME_OVERRIDES.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode()
    data_url = f"data:{mime};base64,{encoded}"

    log.info("Uploading %s (%s, %.0f KB)", path.name, mime, path.stat().st_size / 1024)

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


def upload_resources() -> dict[str, str]:
    """Upload resource files, skipping those already uploaded (unchanged)."""
    metadata = _load_metadata()
    urls = {}

    for f in sorted(RESOURCES_DIR.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue

        current_hash = _file_hash(f)
        cached = metadata.get(f.name)

        if cached and cached.get("hash") == current_hash:
            log.info("Skipping %s (already uploaded, unchanged)", f.name)
            urls[f.name] = cached["url"]
            continue

        url = upload_file(f)
        urls[f.name] = url
        metadata[f.name] = {"hash": current_hash, "url": url}

    _save_metadata(metadata)
    return urls


if __name__ == "__main__":
    if not SEGMIND_API_KEY:
        print("Set SEGMIND_API_KEY in .env first.")
        raise SystemExit(1)

    urls = upload_resources()
    print("\nUploaded URLs:")
    for name, url in urls.items():
        print(f"  {name}: {url}")
