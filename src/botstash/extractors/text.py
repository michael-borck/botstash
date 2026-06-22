"""Plain-text, Markdown/Quarto, and HTML extractors.

These cover lightweight text formats that need no third-party parser:
- ``.txt``         — read verbatim
- ``.md`` / ``.qmd`` — read as text, stripping a leading YAML front-matter block
- ``.html`` / ``.htm`` — strip tags and return readable text (clean for RAG)
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

# Leading YAML front matter: a --- fenced block at the very start of the file.
_FRONT_MATTER = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def extract_text(file_path: Path) -> str:
    """Extract text from a plain-text, Markdown, or Quarto file.

    For ``.md`` and ``.qmd`` files a leading YAML front-matter block is removed
    so it doesn't pollute the embedded content.
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if file_path.suffix.lower() in {".md", ".qmd"}:
        text = _FRONT_MATTER.sub("", text, count=1)
    return text.strip()


class _HTMLTextExtractor(HTMLParser):
    """Collect visible text, dropping script/style and breaking on block tags."""

    _BLOCK = {
        "p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
        "section", "article", "header", "footer", "table", "ul", "ol",
        "blockquote", "pre", "title",
    }
    _SKIP = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag in self._BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def get_text(self) -> str:
        lines = [ln.strip() for ln in "".join(self._parts).splitlines()]
        out: list[str] = []
        blank = False
        for line in lines:
            if line:
                out.append(line)
                blank = False
            elif not blank:
                out.append("")
                blank = True
        return "\n".join(out).strip()


def extract_html(file_path: Path) -> str:
    """Extract clean visible text from an HTML file (tags stripped)."""
    parser = _HTMLTextExtractor()
    parser.feed(file_path.read_text(encoding="utf-8", errors="replace"))
    return parser.get_text()
