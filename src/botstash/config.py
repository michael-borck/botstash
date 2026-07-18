"""Configuration file and environment variable handling."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

from botstash.models import BotStashConfig

_ENV_FILE = ".botstash.env"


def _parse_bool(value: str | None, default: bool) -> bool:
    """Parse a boolean from a string value."""
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


def _load_dotenv_files() -> dict[str, str | None]:
    """Merge the global (home) and local (cwd) dotenv files.

    Local settings override global ones; env vars and CLI args (applied by the
    caller) override both.
    """
    merged: dict[str, str | None] = {}
    # Read global first, then local, so local keys override global ones.
    # If cwd is the home directory both paths point at the same file; loading it
    # twice is harmless since the second update sets identical values.
    for path in (Path.home() / _ENV_FILE, Path.cwd() / _ENV_FILE):
        if path.exists():
            merged.update(dotenv_values(path))
    return merged


def load_config(
    url_override: str | None = None,
    key_override: str | None = None,
    include_answers_override: bool | None = None,
    recursive_override: bool | None = None,
) -> BotStashConfig:
    """Load config with priority: CLI arg > env var > local file > global file."""
    dotenv = _load_dotenv_files()

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

    # Boolean settings: CLI override > env var > dotenv > default
    if include_answers_override is not None:
        include_answers = include_answers_override
    else:
        env_val = os.environ.get("INCLUDE_ANSWERS")
        dot_val = dotenv.get("INCLUDE_ANSWERS")
        include_answers = _parse_bool(env_val or dot_val, default=False)

    if recursive_override is not None:
        recursive = recursive_override
    else:
        env_val = os.environ.get("RECURSIVE")
        dot_val = dotenv.get("RECURSIVE")
        recursive = _parse_bool(env_val or dot_val, default=True)

    return BotStashConfig(
        url=url,
        key=key,
        include_answers=include_answers,
        recursive=recursive,
    )
