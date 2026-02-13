"""
Step 1 — Generate the script content using OpenAI.

Produces structured output:
  - script_text   : the spoken script (used as lyrics for audio generation)
  - social_post   : a short social-media caption
  - video_prompt  : scene description for video generation
  - audio_style   : genre/style tags for audio generation
"""

from __future__ import annotations

import json

from openai import OpenAI

from .config import OPENAI_API_KEY, PROMPTS_DIR, get_logger

log = get_logger("write_script")


def write_script(topic: str | None = None) -> dict:
    """Generate a script and associated content.

    Args:
        topic: Optional topic or theme. If None, the model picks
               a timely topic on its own.

    Returns:
        dict with keys: script_text, social_post, video_prompt, audio_style
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in .env")

    system_prompt = (PROMPTS_DIR / "system_prompt.md").read_text()
    audio_style = (PROMPTS_DIR / "audio_style.md").read_text()

    system_msg = f"""{system_prompt}

---

You will output a JSON object with exactly these keys:

1. "script_text" — The full script (30-60 seconds when spoken aloud,
   roughly 80-150 words). Written as it would be spoken, with natural pauses
   indicated by line breaks. This will be used as lyrics for a spoken-word
   audio track.

2. "social_post" — A punchy social-media caption (1-3 sentences) that teases
   the topic and encourages engagement. Include 2-3 relevant hashtags.

3. "video_prompt" — A one-sentence visual scene description for the video
   background. Keep it cinematic and atmospheric.

4. "audio_style" — Genre and style tags for the audio track, derived from
   the mood of this particular script. Base it on these defaults but adjust
   for the topic:
{audio_style}

Output ONLY the JSON object, no markdown fences or extra text.
"""

    client = OpenAI(api_key=OPENAI_API_KEY)

    user_msg = (
        f"Create a script about: {topic}"
        if topic
        else "Choose a timely, relevant topic and create a script."
    )

    log.info("Generating script — topic: %s", topic or "(auto)")

    response = client.chat.completions.create(
        model="gpt-5-mini",
        # temperature=0.9,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    result = json.loads(raw)

    log.info("Script generated — %d words", len(result["script_text"].split()))
    log.debug("Social post: %s", result["social_post"])

    return result
