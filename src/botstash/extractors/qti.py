"""QTI XML quiz extraction — question text only."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def _strip_ns(tag: str) -> str:
    """Remove XML namespace prefix from a tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _extract_text_recursive(elem: ET.Element) -> str:
    """Extract all text content from an element and its children."""
    parts: list[str] = []
    if elem.text:
        parts.append(elem.text.strip())
    for child in elem:
        parts.append(_extract_text_recursive(child))
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def extract_qti(file_path: Path) -> str:
    """Extract question text from a QTI XML file (1.2 or 2.1 format).

    Returns one question per line. Excludes answer choices and correct answers.
    """
    tree = ET.parse(file_path)  # noqa: S314
    root = tree.getroot()
    questions: list[str] = []

    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        # QTI 1.2: question text in <mattext> inside <presentation>
        if tag == "mattext":
            text = _extract_text_recursive(elem)
            if text and len(text) > 5:
                questions.append(text)
        # QTI 2.1: question text in <prompt>
        elif tag == "prompt":
            text = _extract_text_recursive(elem)
            if text:
                questions.append(text)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return "\n".join(unique)
