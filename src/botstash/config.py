"""Configuration file and environment variable handling."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from botstash.models import BotStashConfig

_ENV_FILE = ".botstash.env"


def load_config(
    url_override: str | None = None,
    key_override: str | None = None,
) -> BotStashConfig:
    """Load AnythingLLM config with priority: CLI arg > env var > dotenv file."""
    dotenv_path = Path.cwd() / _ENV_FILE
    dotenv = dotenv_values(dotenv_path) if dotenv_path.exists() else {}

    url = (
        url_override
        or os.environ.get("ANYTHINGLLM_URL")
        or dotenv.get("ANYTHINGLLM_URL")
    )
    key = (
        key_override
        or os.environ.get("ANYTHINGLLM_KEY")
        or dotenv.get("ANYTHINGLLM_KEY")
    )

    return BotStashConfig(url=url, key=key)
