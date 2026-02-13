# Pastor Al

An automated content pipeline that generates short-form video sermons from an AI pastor — a progressive, robot preacher with a heart for ministry.

The pipeline takes a topic (or picks one automatically), writes a script, generates spoken-word audio, and produces a lip-synced avatar video ready for social media.

## How It Works

The pipeline runs three steps in sequence, each calling a different API:

1. **Script Generation (OpenAI)** — Generates a 30–60 second spoken-word content with a social media caption, a video scene prompt, and audio style tags.

2. **Audio Generation (MusicAPI)** — Sends the script text as lyrics to MusicAPI's Sonic model with spoken-word/lo-fi gospel styling. Polls until the track is ready, then downloads the MP3.

3. **Video Generation (Segmind)** — Submits the audio and an avatar image to Segmind's Infinite Talk endpoint, which produces a lip-synced video of the avatar speaking the sermon.

Each step saves its output to the `output/` directory (`content.json`, `audio.mp3`, `video.mp4`), so steps can be re-run independently.

## Setup

**Requirements:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
uv sync
```

Create a `.env` file in the project root with your API keys:

```
OPENAI_API_KEY=sk-...
MUSICAPI_API_KEY=...
SEGMIND_API_KEY=...
```

Optionally set a custom avatar image:

```
AVATAR_IMAGE_URL=https://...
```

## Usage

Run the full pipeline:

```bash
uv run python main.py
```

Specify a topic:

```bash
uv run python main.py --topic "grace"
```

Run individual steps:

```bash
uv run python main.py --step script              # generate script only
uv run python main.py --step audio               # generate audio (needs script output)
uv run python main.py --step video               # generate video (needs audio output)
uv run python main.py --step script --topic "forgiveness"
```

### Upload Resources

To upload local assets (images, audio) to Segmind's hosted storage:

```bash
uv run python src/upload_assets.py
```

Tracks file hashes so unchanged files are skipped on re-upload.

## Project Structure

```
pastor_al/
├── main.py                  # entrypoint
├── src/
│   ├── pipeline.py          # orchestrates the 3-step workflow
│   ├── write_script.py      # step 1 — OpenAI script generation
│   ├── audio_generation.py  # step 2 — MusicAPI audio generation
│   ├── video_generation.py  # step 3 — Segmind video generation
│   ├── upload_assets.py     # upload local files to Segmind storage
│   ├── config.py            # paths, env vars, API config, logging
│   ├── utils.py             # shared helpers (download, polling)
│   └── prompts/
│       ├── system_prompt.md # Pastor Al's persona and homily structure
│       └── audio_style.md   # spoken-word audio style description
└── output/                  # generated artifacts (gitignored)
```

## Cost Per Video

| Service | Estimated Cost |
|---------|---------------|
| OpenAI  | ~$0.01        |
| MusicAPI    | ~$0.10        |
| Segmind | ~$0.25        |

## Other Ideas

- 15-minute masses from home
- "Chat with God" interactive functionality
