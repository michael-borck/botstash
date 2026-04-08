"""Heuristic and optional AI classification."""

from __future__ import annotations

import re
from pathlib import Path

from botstash.models import ResourceRecord, TagEntry, write_tags

# Pass 1: filename/path keyword mapping
_KEYWORD_MAP: dict[str, list[str]] = {
    "lecture": ["lecture", "slides", "week"],
    "worksheet": ["worksheet", "tutorial", "lab"],
    "assignment": ["assignment", "task", "project"],
    "rubric": ["rubric", "marking", "criteria"],
    "unit_outline": ["outline", "unit guide", "course guide"],
    "quiz": ["quiz", "test"],
    "reading": ["reading", "article", "chapter"],
}

VALID_TYPES = {
    "lecture",
    "worksheet",
    "assignment",
    "rubric",
    "unit_outline",
    "quiz",
    "reading",
    "transcript",
    "video_url",
    "misc",
}


def _classify_by_filename(source_file: str) -> str | None:
    """Pass 1: match keywords against filename and parent folder."""
    name_lower = source_file.lower()
    for doc_type, keywords in _KEYWORD_MAP.items():
        if any(kw in name_lower for kw in keywords):
            return doc_type
    return None


def _classify_by_content(text: str, file_type: str) -> str | None:
    """Pass 2: inspect first 500 chars for structural signals."""
    if file_type in (".vtt", "vtt"):
        return "transcript"
    if file_type in ("url",):
        return "video_url"

    snippet = text[:500].lower()

    # QTI namespace is a strong signal
    if "imsglobal.org/xsd" in snippet and "qti" in snippet:
        return "quiz"

    # Unit outline signals
    if "learning outcomes" in snippet or "unit guide" in snippet:
        return "unit_outline"

    return None


def _extract_week(source_file: str, text: str) -> int | None:
    """Extract week number from filename or text content."""
    # Try filename first
    match = re.search(r"week\s*(\d+)", source_file, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Try first 200 chars of text
    match = re.search(r"week\s*(\d+)", text[:200], re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _derive_title(source_file: str) -> str:
    """Derive a human-readable title from a filename."""
    stem = Path(source_file).stem
    # Replace separators with spaces
    title = stem.replace("_", " ").replace("-", " ")
    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title).strip()
    # Title case
    return title.title()


def classify(
    records: list[ResourceRecord], output_dir: Path
) -> list[TagEntry]:
    """Classify resource records and write extracted text to output_dir.

    Uses a two-pass heuristic approach:
    - Pass 1: filename/path keyword matching
    - Pass 2: content inspection (overrides Pass 1 on high-confidence)
    - Fallback: 'misc'

    Writes extracted text files to output_dir and generates tags.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tags: list[TagEntry] = []

    for record in records:
        # Run both passes
        pass1 = _classify_by_filename(record.source_file)
        pass2 = _classify_by_content(record.extracted_text, record.file_type)

        # Pass 2 overrides Pass 1 on high-confidence matches
        if pass2:
            doc_type = pass2
        elif pass1:
            doc_type = pass1
        else:
            doc_type = "misc"

        # Write extracted text to file
        safe_name = Path(record.source_file).stem + ".txt"
        text_path = output_dir / safe_name
        text_path.write_text(record.extracted_text)

        # Extract metadata
        week = _extract_week(record.source_file, record.extracted_text)
        title = record.title or _derive_title(record.source_file)

        tags.append(
            TagEntry(
                source_file=record.source_file,
                extracted_as=str(text_path),
                type=doc_type,
                title=title,
                week=week,
            )
        )

    # Write tags.json
    write_tags(tags, output_dir / "tags.json")

    return tags
