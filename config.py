# bot/config.py
import os
import logging
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

logger = logging.getLogger(__name__)

def get_env_int(name: str, default: int = 0) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        logger.warning("Env %s should be int, got %r; using default %s", name, v, default)
        return default

def require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Required env var {name} is not set")
    return v

# Core
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # may be None during tests
BASEROW_URL = os.getenv("BASEROW_URL", "http://baserow:80")
BASEROW_JWT = os.getenv("BASEROW_JWT")
BASEROW_DATABASE_ID = get_env_int("BASEROW_DATABASE_ID", 1)
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
KOKORO_URL = os.getenv("KOKORO_URL", "http://kokoro:8880")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_bella")
MANAGER_TELEGRAM_ID = get_env_int("MANAGER_TELEGRAM_ID", 0)

def validate_config():
    """Call at startup to ensure required secrets are present in prod."""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("YOUR_") or TELEGRAM_TOKEN.strip() == "":
        raise RuntimeError("TELEGRAM_TOKEN is missing or placeholder. Set it via env or .env file.")
