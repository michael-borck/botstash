"""Log video/external URLs found in manifests and HTML content."""

from __future__ import annotations

import re
from pathlib import Path


def extract_urls(html_content: str) -> list[str]:
    """Extract URLs from href and src attributes in HTML content."""
    pattern = r'(?:href|src)\s*=\s*["\']([^"\']+)["\']'
    urls = re.findall(pattern, html_content, re.IGNORECASE)
    return [u for u in urls if u.startswith(("http://", "https://"))]


def log_urls(urls: list[str], context: str, output_path: Path) -> None:
    """Append URLs with their source context to a log file."""
    if not urls:
        return
    with open(output_path, "a") as f:
        for url in urls:
            f.write(f"[{context}] {url}\n")
