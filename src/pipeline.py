"""
AI influencer content pipeline.

Orchestrates the 4-step generation process:
  1. Write script    (OpenAI)
  2. Generate image  (Segmind Flux Schnell)
  3. Generate audio  (MusicAPI)
  4. Generate video  (Segmind Infinite Talk)

Usage:
  python main.py                         # auto-selects topic
  python main.py --topic "grace"         # specific topic
  python main.py --step script           # run only step 1
  python main.py --step image            # run only step 2 (needs prior output)
  python main.py --step audio            # run only step 3 (needs prior output)
  python main.py --step video            # run only step 4 (needs prior output)
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, Future

from .config import OUTPUT_DIR, get_logger
from .write_script import write_script
from .audio_generation import generate_audio
from .image_generation import generate_image
from .video_generation import generate_video

log = get_logger("pipeline")

CONTENT_FILE = OUTPUT_DIR / "content.json"


def run_script(topic: str | None) -> dict:
    content = write_script(topic)
    CONTENT_FILE.write_text(json.dumps(content, indent=2))
    log.info("Content written to %s", CONTENT_FILE)
    return content


def run_image(content: dict) -> tuple[str, str]:
    return generate_image(video_prompt=content["video_prompt"])


def run_audio(content: dict) -> tuple[str, str]:
    return generate_audio(
        script_text=content["script_text"],
        audio_style=content["audio_style"],
    )


def run_video(content: dict, audio_url: str, image_url: str | None = None) -> str:
    return generate_video(
        audio_url=audio_url,
        video_prompt=content["video_prompt"],
        image_url=image_url,
    )


def load_content() -> dict:
    if not CONTENT_FILE.exists():
        log.error("No content file found at %s — run the script step first", CONTENT_FILE)
        sys.exit(1)
    return json.loads(CONTENT_FILE.read_text())


def main() -> None:
    parser = argparse.ArgumentParser(description="AI influencer content pipeline")
    parser.add_argument("--topic", type=str, default=None, help="Topic or theme for the script")
    parser.add_argument(
        "--step",
        choices=["script", "image", "audio", "video"],
        default=None,
        help="Run a single step instead of the full pipeline",
    )
    args = parser.parse_args()

    log.info("=== Pipeline starting ===")

    if args.step == "script" or args.step is None:
        content = run_script(args.topic)
        log.info("--- Step 1 complete: script written ---")
        print(f"\n{'='*50}")
        print("SCRIPT:")
        print(content["script_text"])
        print(f"\nSOCIAL POST:")
        print(content["social_post"])
        print(f"{'='*50}\n")
    else:
        content = load_content()

    image_url = None
    audio_url = None

    # Image and audio are independent — run them in parallel during full pipeline
    if args.step is None:
        log.info("Running image + audio generation in parallel")
        with ThreadPoolExecutor(max_workers=2) as pool:
            image_future: Future = pool.submit(run_image, content)
            audio_future: Future = pool.submit(run_audio, content)

            image_path, image_url = image_future.result()
            log.info("--- Step 2 complete: image generated ---")
            print(f"Image: {image_path}")

            audio_path, audio_url = audio_future.result()
            log.info("--- Step 3 complete: audio generated ---")
            print(f"Audio: {audio_path}")

    elif args.step == "image":
        image_path, image_url = run_image(content)
        log.info("--- Step 2 complete: image generated ---")
        print(f"Image: {image_path}")

    elif args.step == "audio":
        audio_path, audio_url = run_audio(content)
        log.info("--- Step 3 complete: audio generated ---")
        print(f"Audio: {audio_path}")

    if args.step == "video" or args.step is None:
        if image_url is None:
            # Cross-session: load persisted URL from image step
            url_file = OUTPUT_DIR / "image_url.txt"
            if url_file.exists():
                image_url = url_file.read_text().strip()

        if audio_url is None:
            # Cross-session: load persisted URL from audio step
            url_file = OUTPUT_DIR / "audio_url.txt"
            if not url_file.exists():
                log.error("No audio URL found — run the audio step first")
                sys.exit(1)
            audio_url = url_file.read_text().strip()

        video_path = run_video(content, audio_url, image_url=image_url)
        log.info("--- Step 4 complete: video generated ---")
        print(f"Video: {video_path}")

    log.info("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
