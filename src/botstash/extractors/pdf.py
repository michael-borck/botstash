"""PDF text extraction.

Prefers pymupdf (MuPDF) which handles broken CMap font encodings
(common in university-generated PDFs). Falls back to pdfminer.six.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pdf(file_path: Path) -> str:
    """Extract plain text from a PDF file."""
    # Try pymupdf first — handles broken font encodings correctly
    try:
        import pymupdf

        doc = pymupdf.open(str(file_path))
        text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
        if text.strip():
            return text.strip()
    except ImportError:
        pass
    except Exception:
        logger.debug("pymupdf extraction failed, falling back to pdfminer")

    # Fallback to pdfminer.six
    from pdfminer.high_level import extract_text

    return extract_text(str(file_path)).strip()
