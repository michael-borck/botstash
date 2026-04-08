# BotStash

A CLI tool and lightweight WebUI that extracts course content (PDFs, DOCX, PPTX, VTT transcripts, IMSCC exports), classifies it, and uploads to an [AnythingLLM](https://anythingllm.com/) workspace for embedded chatbots.

## Features

- **Folder-first scanning** — point at a folder, BotStash figures out the rest
- **Multi-format extraction** — PPTX, DOCX, PDF, VTT, QTI quizzes, IMSCC exports
- **Recursive ZIP handling** — nested ZIPs and IMSCC archives are auto-detected
- **Structured unit outline parsing** — extracts assessments, schedules, learning outcomes with Bloom's taxonomy
- **Auto-classification** — heuristic tagging of content types (lecture, worksheet, assignment, etc.)
- **AnythingLLM integration** — uploads documents, manages workspaces, retrieves embed code
- **WebUI** — FastAPI + Jinja2 interface for non-terminal users

## Installation

```bash
pip install botstash
```

## Quick Start

```bash
# Full pipeline — point at a folder
botstash run ./course-materials/ --workspace ISYS2001

# Two-step workflow (extract, review, embed)
botstash extract ./course-materials/ --output ./staging/
# ... review staging/tags.json ...
botstash embed ./staging/ --workspace ISYS2001

# Include quiz answer choices
botstash extract ./folder/ --include-answers

# Non-recursive (top-level only)
botstash extract ./folder/ --no-recursive

# Launch WebUI
botstash serve
```

## Configuration

Settings are resolved in priority order: CLI flag > environment variable > `.botstash.env` file.

```bash
# Scaffold a config file
botstash init
```

`.botstash.env`:
```
ANYTHINGLLM_URL=http://localhost:3001
ANYTHINGLLM_KEY=your-api-key
INCLUDE_ANSWERS=false
RECURSIVE=true
```

## Development

```bash
git clone https://github.com/michael-borck/botstash.git
cd botstash
uv sync --dev

uv run ruff check src/ tests/
uv run pytest
```

## License

MIT
