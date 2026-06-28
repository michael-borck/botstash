# BotStash

A CLI tool and lightweight WebUI that extracts course content (PDFs, DOCX, PPTX, VTT transcripts, IMSCC exports, plus Markdown/Quarto, HTML and plain text), classifies it, and uploads to an [AnythingLLM](https://anythingllm.com/) workspace for embedded chatbots.

## Features

- **Folder-first scanning** — point at a folder, BotStash figures out the rest
- **Multi-format extraction** — PPTX, DOCX, PDF, VTT, QTI quizzes, IMSCC exports, Markdown/Quarto (`.md`/`.qmd`), HTML (`.html`/`.htm`), plain text (`.txt`)
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

# Update an existing workspace cleanly (clears old docs first — no duplicates)
botstash run ./course-materials/ --workspace ISYS2001 --reset

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

## Provisioning persona chatbots

BotStash can also provision multiple **in-character persona bots** (a simulated organisation's staff, for example) from a manifest. Each persona gets its own workspace, a system-prompt identity, a personal backstory plus any shared documents, and an embed widget whose id is written back into the persona's page file.

```bash
# personas.json lists personas (slug, prompt, backstory, page), shared docs, allowlist_domains
botstash persona personas.json --url http://localhost:3001 --key $ANYTHINGLLM_KEY

# Re-run cleanly (--reset clears each workspace's documents first)
botstash persona personas.json --reset
```

Manifest schema (paths resolve relative to the manifest file):

```json
{
  "shared_docs": ["company_overview.md"],
  "allowlist_domains": ["example.org"],
  "personas": [
    {"slug": "priya_nair", "prompt": "bots/priya_nair/prompt.txt",
     "backstory": "_backstories/priya_nair_cfo.md",
     "page": "bots/priya_nair/index.qmd"}
  ]
}
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
