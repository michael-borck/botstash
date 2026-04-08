"""Bespoke unit outline extraction plugin."""

from __future__ import annotations

from pathlib import Path


def extract_unit_outline(file_path: str) -> str:
    """Extract text from a unit outline document (DOCX or PDF).

    Takes an absolute path to a DOCX/PDF unit outline.
    Returns extracted plain text as a single string.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".docx":
        from botstash.extractors.docx import extract_docx

        return extract_docx(path)
    elif suffix == ".pdf":
        from botstash.extractors.pdf import extract_pdf

        return extract_pdf(path)
    else:
        msg = f"Unsupported unit outline format: {suffix}"
        raise ValueError(msg)
