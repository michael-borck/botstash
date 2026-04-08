"""Heuristic and optional AI classification."""

from __future__ import annotations

import hashlib
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

# Signals for unit outline content detection
_OUTLINE_SIGNALS = [
    r"assessment\s+(?:schedule|summary|overview|tasks?)",
    r"learning\s+outcomes?",
    r"(?:weekly|teaching|program)\s+(?:schedule|calendar)",
    r"credit\s+(?:points?|value)",
    r"(?:unit|course)\s+(?:description|guide|outline)",
    r"pre-?requisite",
]


def _classify_by_filename(source_file: str) -> str | None:
    """Pass 1: match keywords against filename and parent folder."""
    name_lower = source_file.lower()
    for doc_type, keywords in _KEYWORD_MAP.items():
        if any(kw in name_lower for kw in keywords):
            return doc_type
    return None


def _classify_by_content(text: str, file_type: str) -> str | None:
    """Pass 2: inspect content for structural signals."""
    if file_type in (".vtt", "vtt"):
        return "transcript"
    if file_type in ("url",):
        return "video_url"

    snippet = text[:2000].lower()

    # QTI namespace is a strong signal
    if "imsglobal.org/xsd" in snippet and "qti" in snippet:
        return "quiz"

    # Unit outline: check for multiple structural signals
    signal_count = sum(
        1
        for pattern in _OUTLINE_SIGNALS
        if re.search(pattern, snippet, re.IGNORECASE)
    )
    if signal_count >= 2:
        return "unit_outline"

    return None


def _extract_week(source_file: str, text: str) -> int | None:
    """Extract week number from filename or text content."""
    match = re.search(r"week\s*(\d+)", source_file, re.IGNORECASE)
    if match:
        return int(match.group(1))

    match = re.search(r"week\s*(\d+)", text[:200], re.IGNORECASE)
    if match:
        return int(match.group(1))

    return None


def _derive_title(source_file: str) -> str:
    """Derive a human-readable title from a filename."""
    stem = Path(source_file).stem
    title = stem.replace("_", " ").replace("-", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title.title()


def _safe_filename(source_file: str, used: set[str]) -> str:
    """Generate a unique filename for extracted text."""
    stem = Path(source_file).stem
    name = f"{stem}.txt"
    if name not in used:
        used.add(name)
        return name
    # Collision: append short hash of full source path
    h = hashlib.md5(source_file.encode()).hexdigest()[:6]  # noqa: S324
    name = f"{stem}_{h}.txt"
    used.add(name)
    return name


def classify(
    records: list[ResourceRecord], output_dir: Path
) -> list[TagEntry]:
    """Classify resource records and write extracted text to output_dir.

    Uses a two-pass heuristic approach:
    - Pass 1: filename/path keyword matching
    - Pass 2: content inspection (overrides Pass 1 on high-confidence)
    - Fallback: 'misc'

    When a document is classified as unit_outline and is a DOCX/PDF,
    re-extracts using the structured outline extractor.

    Writes extracted text files to output_dir and generates tags.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tags: list[TagEntry] = []
    used_names: set[str] = set()

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

        # Re-extract unit outlines with structured extractor
        extracted_text = record.extracted_text
        if doc_type == "unit_outline" and record.file_type in (
            ".docx", ".pdf"
        ):
            try:
                from botstash.extractors.unit_outline import (
                    extract_unit_outline,
                )

                extracted_text = extract_unit_outline(record.source_file)
            except Exception:
                pass  # Fall back to raw text

        # Write extracted text to file (collision-safe)
        safe_name = _safe_filename(record.source_file, used_names)
        text_path = output_dir / safe_name
        text_path.write_text(extracted_text)

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
