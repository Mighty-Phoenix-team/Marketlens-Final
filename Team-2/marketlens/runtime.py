"""Bounded local runtime settings; existing .env and model choice are retained."""
import math
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", encoding="utf-8-sig", override=False)


class MissingGeminiKey(ValueError):
    pass


def number_setting(name, default, minimum, maximum):
    try:
        value = float(os.getenv(name, str(default)))
        if not math.isfinite(value):
            raise ValueError
    except ValueError:
        value = default
    return min(maximum, max(minimum, value))


def explanation_timeout():
    # At most 85s Gemini + 20s asset HTTP budget, below dashboard's 120s wait.
    return number_setting("MARKETLENS_EXPLANATION_TIMEOUT_SECONDS", 60, 1, 85)


def explanation_ttl():
    return number_setting("MARKETLENS_EXPLANATION_CACHE_TTL_SECONDS", 900, 0, 3600)
