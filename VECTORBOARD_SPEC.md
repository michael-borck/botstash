# VectorBoard — Project Specification v0.1

> A CLI tool and lightweight WebUI that ingests an LMS course export (Blackboard IMSCC or Canvas) and a folder of Echo360 VTT transcripts, extracts and classifies content, uploads it to an AnythingLLM workspace, and returns embeddable chatbot code for pasting into a course page.

---

## Name Rationale

**VectorBoard** — vector embeddings + "board" as a generic term for a course/learning board. Intentionally LMS-agnostic so it survives the move from Blackboard to Canvas without renaming. Python package name: `vectorboard`.

---

## Goals

- Give students a citeable, course-aware AI chatbot embedded directly in their LMS page
- Require minimal technical effort from the lecturer (one command or a simple WebUI)
- Support both automated and manually-reviewed classification workflows
- Be LMS-portable: IMSCC is the common cartridge format shared by Blackboard and Canvas

---

## Architecture

```
vectorboard/
├── cli.py                  # Click-based entry points
├── config.py               # Config file + env var handling
├── pipeline.py             # Orchestrates the full run
├── ingester/
│   ├── imscc.py            # Unzip + walk IMSCC/common cartridge structure
│   └── transcript.py       # VTT folder ingestion
├── extractors/
│   ├── docx.py
│   ├── pdf.py
│   ├── pptx.py
│   ├── vtt.py              # VTT → clean text (timestamps stripped)
│   ├── qti.py              # Blackboard/Canvas quiz XML → questions only
│   ├── url_tracker.py      # Log video/external URLs found in manifests
│   └── unit_outline.py     # Bespoke plugin (to be provided at build time)
├── classifier/
│   └── auto.py             # Heuristic + optional AI classification
├── anythingllm/
│   └── client.py           # AnythingLLM REST API wrapper
└── webui/
    └── app.py              # FastAPI + Jinja2 simple UI
```

---

## CLI Commands

### Full pipeline (default usage)

```bash
vectorboard run course.zip transcripts/ \
  --workspace ISYS2001 \
  --url https://your-anythingllm.instance \
  --key YOUR_API_KEY
```

### Two-step workflow (for manual tag review)

```bash
# Step 1: extract and auto-classify, write tags file
vectorboard extract course.zip transcripts/ --output ./staging/

# Step 2 (optional): open staging/tags.json in any editor and adjust types/titles

# Step 3: embed using the (possibly edited) tags file
vectorboard embed ./staging/ --workspace ISYS2001 --tags staging/tags.json

# Step 4: retrieve embed code
vectorboard chatbot ISYS2001
```

### Reset a workspace (new semester)

```bash
vectorboard embed ./staging/ --workspace ISYS2001 --reset
```

`--reset` clears all documents from the workspace before re-uploading. The workspace itself (and its embed code URL) is preserved, so the LMS page never needs updating mid-year.

---

## Workspace Strategy

- **One workspace per unit code** (e.g. `ISYS2001`, `ISYS6020`)
- Semester changeover is handled by running with `--reset` — workspace identity and embed URL remain stable
- Archiving, deletion, and multi-semester history management are intentionally out of scope; these are handled manually in the AnythingLLM UI if needed

---

## Document Classification

Auto-classification uses a two-pass approach:

**Pass 1 — Filename and path heuristics**

Keywords matched against filename and parent folder name (case-insensitive):

| Keywords | Assigned type |
|---|---|
| `lecture`, `slides`, `week` | `lecture` |
| `worksheet`, `tutorial`, `lab` | `worksheet` |
| `assignment`, `task`, `project` | `assignment` |
| `rubric`, `marking`, `criteria` | `rubric` |
| `outline`, `unit guide`, `course guide` | `unit_outline` |
| `quiz`, `test` | `quiz` |
| `reading`, `article`, `chapter` | `reading` |
| *(VTT file)* | `transcript` |
| *(URL-only entry)* | `video_url` |

**Pass 2 — Content heuristics**

First 500 characters of extracted text are inspected for structural signals (e.g. QTI XML namespace → always `quiz`; "Learning Outcomes" header → likely `unit_outline`). Pass 2 overrides Pass 1 on high-confidence matches.

**Fallback:** `misc`

### Tags file format (`tags.json`)

Generated automatically after extraction. Edit before the embed step to override any classification.

```json
[
  {
    "source_file": "Week1_Intro.pptx",
    "extracted_as": "staging/Week1_Intro.txt",
    "type": "lecture",
    "title": "Week 1: Introduction to Information Systems",
    "week": 1
  },
  {
    "source_file": "Assessment1_Rubric.docx",
    "extracted_as": "staging/Assessment1_Rubric.txt",
    "type": "rubric",
    "title": "Assessment 1 Rubric",
    "week": null
  }
]
```

Valid `type` values: `lecture`, `worksheet`, `assignment`, `rubric`, `unit_outline`, `quiz`, `reading`, `transcript`, `video_url`, `misc`

---

## Extractor Behaviour

| Source format | Output | Notes |
|---|---|---|
| PPTX | Plain text per slide, slide number preserved as a heading | Speaker notes included |
| DOCX | Plain text, headings preserved as markdown-style markers | Unit outline uses bespoke plugin |
| PDF | Plain text via `pdfminer.six` or `pymupdf` | `--ocr` flag available as fallback |
| VTT | Clean plain text, timestamps stripped, filename used as title | One text file per transcript |
| QTI XML (quizzes) | Question text only, one question per line | Answer choices and correct answers excluded (student-facing) |
| Video / external URLs | Written to `urls_log.txt` with the page/item context they appeared in | Not fetched or scraped |

### Unit outline extraction

A bespoke Python plugin handles unit outlines. Interface expected at build time:

```python
def extract_unit_outline(file_path: str) -> str:
    """Takes an absolute path to a DOCX/PDF unit outline.
    Returns extracted plain text as a single string."""
```

---

## AnythingLLM Integration

Uses the AnythingLLM REST API. Key operations:

| Operation | API call |
|---|---|
| Check workspace exists | `GET /api/v1/workspaces` |
| Create workspace | `POST /api/v1/workspace/new` |
| Upload document | `POST /api/v1/document/upload` |
| Move document to workspace | `POST /api/v1/workspace/{slug}/update-embeddings` |
| Reset workspace documents | `DELETE` or re-embed with `--reset` flag |
| Get chatbot embed code | `GET /api/v1/workspace/{slug}/chatbot-embed` *(confirm endpoint)* |

### Configuration

Credentials are never passed as plain CLI arguments. Set via:

- A `.vectorboard.env` file in the working directory, or
- Environment variables: `ANYTHINGLLM_URL`, `ANYTHINGLLM_KEY`

A `vectorboard init` command scaffolds the `.vectorboard.env` file interactively.

---

## Staging and Cleanup

- Extracted text files are written to a `./staging/` directory during processing
- After a successful embed, staging files are deleted automatically unless `--keep-staging` is passed
- The `tags.json` file is always retained after a run (useful for auditing what was embedded)

---

## WebUI

A lightweight FastAPI + Jinja2 interface for lecturers who prefer not to use the terminal.

**Workflow:**

1. Upload course ZIP and transcript folder
2. Review extracted items with auto-assigned types (inline dropdowns to override before embedding)
3. Click **Embed to AnythingLLM**
4. Copy the chatbot embed code from the result panel

The WebUI is a thin wrapper around the same pipeline — no separate logic. Launch with:

```bash
vectorboard serve
```

---

## Out of Scope (v1)

- Fetching or scraping external URLs
- Semester archiving or workspace deletion
- Multi-workspace merge
- Direct LMS API integration (embed code is copied manually)
- LMS platforms other than Blackboard/Canvas IMSCC format
- Student authentication or access control on the WebUI

---

## Open Questions (resolve at build time)

1. **Unit outline plugin** — confirm function signature and whether it handles both DOCX and PDF inputs
2. **AnythingLLM embed code** — confirm whether the embed snippet is retrievable via API or only from the UI; if UI-only, the `chatbot` command prints the workspace URL and instructs the user to copy from there
3. **AnythingLLM document metadata** — determine which metadata fields (week number, doc type) can be passed at upload time to improve citation quality in responses
4. **Canvas differences** — confirm whether Canvas IMSCC exports use the same QTI format and manifest structure as Blackboard; adjust `imscc.py` accordingly

---

## Suggested Dependency Stack

| Purpose | Library |
|---|---|
| CLI framework | `click` |
| WebUI | `fastapi` + `jinja2` + `uvicorn` |
| PPTX extraction | `python-pptx` |
| DOCX extraction | `python-docx` |
| PDF extraction | `pdfminer.six` or `pymupdf` |
| VTT parsing | `webvtt-py` |
| HTTP client (AnythingLLM API) | `httpx` |
| Config / env | `python-dotenv` |
| Packaging | `pyproject.toml` with `pip install -e .` |

---

*VectorBoard v0.1 spec — generated April 2026. Continue build in a Claude Code session.*
