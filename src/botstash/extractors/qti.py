"""QTI XML quiz extraction — questions with optional answer choices."""

from __future__ import annotations

import string
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


def _extract_answers_v12(item: ET.Element) -> list[str]:
    """Extract answer choices from a QTI 1.2 item (response_label > mattext)."""
    answers: list[str] = []
    for elem in item.iter():
        tag = _strip_ns(elem.tag)
        if tag == "response_label":
            for child in elem.iter():
                if _strip_ns(child.tag) == "mattext":
                    text = _extract_text_recursive(child)
                    if text:
                        answers.append(text)
    return answers


def _extract_answers_v21(item: ET.Element) -> list[str]:
    """Extract answer choices from a QTI 2.1 item (simpleChoice)."""
    answers: list[str] = []
    for elem in item.iter():
        if _strip_ns(elem.tag) == "simpleChoice":
            text = _extract_text_recursive(elem)
            if text:
                answers.append(text)
    return answers


def _format_answers(answers: list[str]) -> str:
    """Format answer choices as lettered options."""
    letters = string.ascii_uppercase
    lines: list[str] = []
    for i, answer in enumerate(answers):
        label = letters[i] if i < len(letters) else str(i + 1)
        lines.append(f"  {label}. {answer}")
    return "\n".join(lines)


def extract_qti(
    file_path: Path, *, include_answers: bool = False
) -> str:
    """Extract questions from a QTI XML file (1.2 or 2.1 format).

    Returns one question per line. When include_answers is True,
    answer choices are listed below each question as lettered options.
    Correct answer markers are never included.
    """
    tree = ET.parse(file_path)  # noqa: S314
    root = tree.getroot()
    output_lines: list[str] = []

    # Process QTI 1.2 items
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag == "item":
            # Extract question from presentation > mattext
            question = None
            for child in elem.iter():
                if _strip_ns(child.tag) == "presentation":
                    for mat in child.iter():
                        if _strip_ns(mat.tag) == "mattext":
                            text = _extract_text_recursive(mat)
                            if text and len(text) > 5:
                                question = text
                                break
                    break

            if question:
                output_lines.append(question)
                if include_answers:
                    answers = _extract_answers_v12(elem)
                    if answers:
                        output_lines.append(_format_answers(answers))

    # If no QTI 1.2 items found, try QTI 2.1
    if not output_lines:
        for elem in root.iter():
            tag = _strip_ns(elem.tag)
            if tag == "assessmentItem":
                question = None
                for child in elem.iter():
                    if _strip_ns(child.tag) == "prompt":
                        question = _extract_text_recursive(child)
                        break

                if question:
                    output_lines.append(question)
                    if include_answers:
                        answers = _extract_answers_v21(elem)
                        if answers:
                            output_lines.append(
                                _format_answers(answers)
                            )

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for line in output_lines:
        if line not in seen:
            seen.add(line)
            unique.append(line)

    return "\n".join(unique)
