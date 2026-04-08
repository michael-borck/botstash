"""PDF text extraction via pdfminer.six."""

from __future__ import annotations

from pathlib import Path

from pdfminer.high_level import extract_text


def extract_pdf(file_path: Path) -> str:
    """Extract plain text from a PDF file."""
    return extract_text(str(file_path)).strip()
