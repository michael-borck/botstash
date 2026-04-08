"""DOCX text extraction with heading preservation."""

from __future__ import annotations

from pathlib import Path

import docx


def extract_docx(file_path: Path) -> str:
    """Extract plain text from a DOCX file, preserving headings as markdown."""
    doc = docx.Document(str(file_path))
    lines: list[str] = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style = para.style.name if para.style else ""
        if style.startswith("Heading"):
            try:
                level = int(style.split()[-1])
            except (ValueError, IndexError):
                level = 1
            lines.append(f"{'#' * level} {text}")
        else:
            lines.append(text)
    return "\n\n".join(lines)
