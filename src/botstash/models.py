"""Shared data structures for BotStash."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class BotStashConfig:
    """AnythingLLM connection configuration."""

    url: str | None = None
    key: str | None = None


@dataclass
class ResourceRecord:
    """A single resource extracted from a course export or transcript folder."""

    source_file: str
    extracted_text: str
    file_type: str  # file extension or manifest resource type
    title: str


@dataclass
class TagEntry:
    """Classification tag for an extracted resource (maps to tags.json)."""

    source_file: str
    extracted_as: str
    type: str
    title: str
    week: int | None = None


def write_tags(tags: list[TagEntry], path: Path) -> None:
    """Serialize tag entries to a JSON file."""
    path.write_text(
        json.dumps([asdict(t) for t in tags], indent=2, ensure_ascii=False) + "\n"
    )


def read_tags(path: Path) -> list[TagEntry]:
    """Deserialize tag entries from a JSON file."""
    data = json.loads(path.read_text())
    return [TagEntry(**entry) for entry in data]
