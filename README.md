# VectorBoard

A CLI tool and lightweight WebUI that ingests LMS course exports (Blackboard IMSCC / Canvas) and Echo360 VTT transcripts, uploads content to an [AnythingLLM](https://anythingllm.com/) workspace, and returns embeddable chatbot code for pasting into a course page.

## Features

- **IMSCC ingestion** — unzips and walks Blackboard/Canvas common cartridge exports
- **Transcript ingestion** — processes folders of Echo360 VTT files
- **Multi-format extraction** — PPTX, DOCX, PDF, VTT, QTI quizzes
- **Auto-classification** — heuristic tagging of content types (lecture, worksheet, assignment, etc.)
- **AnythingLLM integration** — uploads documents, manages workspaces, retrieves embed code
- **WebUI** — FastAPI + Jinja2 interface for non-terminal users

## Installation

```bash
pip install vector-board
```

## Quick Start

```bash
# Full pipeline
vectorboard run course.zip transcripts/ \
  --workspace ISYS2001 \
  --url https://your-anythingllm.instance \
  --key YOUR_API_KEY

# Two-step workflow (extract, review, embed)
vectorboard extract course.zip transcripts/ --output ./staging/
# ... review staging/tags.json ...
vectorboard embed ./staging/ --workspace ISYS2001

# Launch WebUI
vectorboard serve
```

## Development

```bash
# Clone and install in dev mode
git clone https://github.com/michaelborck/vector-board.git
cd vector-board
uv sync --dev

# Run checks
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## License

MIT
