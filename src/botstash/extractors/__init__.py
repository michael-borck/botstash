"""Extractor registry and dispatcher."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from botstash.extractors.docx import extract_docx
from botstash.extractors.pdf import extract_pdf
from botstash.extractors.pptx import extract_pptx
from botstash.extractors.qti import extract_qti
from botstash.extractors.vtt import extract_vtt

EXTRACTOR_REGISTRY: dict[str, Callable[[Path], str]] = {
    ".vtt": extract_vtt,
    ".docx": extract_docx,
    ".pdf": extract_pdf,
    ".pptx": extract_pptx,
    ".xml": extract_qti,
}


def extract_file(file_path: Path) -> str | None:
    """Extract text from a file using the appropriate extractor.

    Returns None if no extractor is registered for the file type.
    """
    extractor = EXTRACTOR_REGISTRY.get(file_path.suffix.lower())
    if extractor is None:
        return None
    return extractor(file_path)
