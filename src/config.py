import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# ── paths ──────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = SRC_DIR / "prompts"
RESOURCES_DIR = SRC_DIR / "resources"
LOGS_DIR = ROOT_DIR / "logs"
OUTPUT_DIR = ROOT_DIR / "output"

LOGS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── env ────────────────────────────────────────────────────────────────────
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
MUSICAPI_API_KEY = os.environ.get("MUSICAPI_API_KEY", "")
SEGMIND_API_KEY = os.environ.get("SEGMIND_API_KEY", "")

# ── MusicAPI config ───────────────────────────────────────────────────────
MUSICAPI_BASE_URL = "https://api.musicapi.ai"
MUSICAPI_MODEL = "sonic-v4-5"

# ── Segmind / Higgsfield config ───────────────────────────────────────────
SEGMIND_BASE_URL = "https://api.segmind.com"

# Avatar image + test audio hosted on Segmind storage
AVATAR_IMAGE_URL = os.environ.get(
    "AVATAR_IMAGE_URL",
    "https://images.segmind.com/assets/benwortman@gmail.com/images/a49022a3-ad22-46e8-9a3f-41d74437c475.jpg",
)
TEST_AUDIO_URL = os.environ.get(
    "TEST_AUDIO_URL",
    "https://images.segmind.com/assets/benwortman@gmail.com/audios/fdda7849-17ec-4105-ad7d-e06ed6cae18c.mp3", # beloved
    # "https://images.segmind.com/assets/benwortman@gmail.com/audios/19c9fb83-0ef4-4d94-a935-046745233bf9.mp3", # greeting
)

# ── logging ────────────────────────────────────────────────────────────────
LOG_FILE = LOGS_DIR / "pastor_al.log"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter(
            "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"
        )

        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)

        logger.addHandler(fh)
        logger.addHandler(ch)
    return logger
