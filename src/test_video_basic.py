import requests
import json

from config import (
    OUTPUT_DIR,
    AVATAR_IMAGE_URL,
    SEGMIND_API_KEY,
    SEGMIND_BASE_URL,
    TEST_AUDIO_URL,
    get_logger,
)

url = "https://api.segmind.com/v1/infinite-talk"
headers = {
    "x-api-key": SEGMIND_API_KEY,
    "Content-Type": "application/json"
}

data = {
    # "image_url": "https://segmind-resources.s3.amazonaws.com/input/74bce37e-151d-4923-a56f-b5f9ce6e5134-601140c8-73e5-4490-8911-e6c7d3dc0e70-infinite_talk_ip.webp",
    "image": AVATAR_IMAGE_URL,
    # "audio_url": "https://segmind-resources.s3.amazonaws.com/input/ce1dcce7-c5b1-4cf6-a42f-65bed682a44a-news-reading-small.mp3",
    "audio": TEST_AUDIO_URL,
    "prompt": "Robot pastor preeching to his audience from inside his robot church",
    "seed": 42424242,
    "resolution": "480p",
    "fps":16
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    content_type = response.headers.get("Content-Type", "")
    
    # Response might be raw video bytes or JSON
    if "application/json" in content_type or "text/" in content_type:
        try:
            body = response.json()
            print(json.dumps(body, indent=2))
        except Exception:
            print(response.text[:500])
        response.raise_for_status()

        # JSON response — extract video URL and download
        from video_generation import _extract_or_poll, _download

        video_url = _extract_or_poll(body)
        out = OUTPUT_DIR / "test_video.mp4"
        _download(video_url, out)
    else:
        # Binary response — the body IS the video
        response.raise_for_status()
        out = OUTPUT_DIR / "test_video.mp4"
        out.write_bytes(response.content)

    size_kb = out.stat().st_size / 1024
    print(f"\nVideo saved to {out} ({size_kb:.0f} KB)")

