"""VTT to clean text conversion (timestamps stripped)."""

from __future__ import annotations

from pathlib import Path

import webvtt


def extract_vtt(file_path: Path) -> str:
    """Extract plain text from a VTT file, stripping all timestamps."""
    captions = webvtt.read(str(file_path))
    lines: list[str] = []
    for caption in captions:
        text = caption.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)
