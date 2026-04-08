"""Structured unit outline extraction.

Extracts raw text from a DOCX/PDF unit outline and then parses it into
structured sections (metadata, assessments, weekly schedule, learning
outcomes, textbooks). Returns well-formatted markdown that a chatbot
can reliably answer questions from.

Ported from the curriculum-curator project's regex-based parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class _Assessment:
    title: str
    weight: float = 0.0
    due_week: int | None = None
    category: str = "assignment"


@dataclass
class _Week:
    week_number: int
    topic: str
    activities: list[str] = field(default_factory=list)


@dataclass
class _LearningOutcome:
    code: str
    description: str
    bloom_level: str = "understand"


@dataclass
class _Textbook:
    title: str
    required: bool = True


@dataclass
class _OutlineData:
    unit_code: str | None = None
    unit_title: str | None = None
    description: str | None = None
    credit_points: int | None = None
    year: int | None = None
    semester: str | None = None
    prerequisites: str | None = None
    delivery_mode: str | None = None
    learning_outcomes: list[_LearningOutcome] = field(default_factory=list)
    weekly_schedule: list[_Week] = field(default_factory=list)
    assessments: list[_Assessment] = field(default_factory=list)
    textbooks: list[_Textbook] = field(default_factory=list)
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Bloom's taxonomy guesser
# ---------------------------------------------------------------------------

_BLOOM_KEYWORDS: dict[str, list[str]] = {
    "remember": [
        "list", "define", "identify", "recall", "name", "state", "recognise",
    ],
    "understand": [
        "describe", "explain", "summarise", "interpret", "discuss",
        "classify", "compare",
    ],
    "apply": [
        "apply", "demonstrate", "use", "implement", "solve", "calculate",
    ],
    "analyse": [
        "analyse", "analyze", "examine", "differentiate", "investigate",
    ],
    "evaluate": [
        "evaluate", "assess", "justify", "critique", "judge", "recommend",
    ],
    "create": [
        "create", "design", "develop", "construct", "produce", "propose",
    ],
}


def _guess_bloom(text: str) -> str:
    """Guess Bloom's taxonomy level from the first verb in outcome text."""
    lower = text.lower().strip()
    for level, keywords in reversed(list(_BLOOM_KEYWORDS.items())):
        for kw in keywords:
            if lower.startswith(kw) or re.search(rf"\b{kw}\b", lower[:60]):
                return level
    return "understand"


# ---------------------------------------------------------------------------
# Assessment category guesser
# ---------------------------------------------------------------------------


def _guess_category(title: str) -> str:
    """Guess assessment category from title keywords."""
    lower = title.lower()
    if any(w in lower for w in ("exam", "test", "quiz")):
        return "exam"
    if any(w in lower for w in ("report", "essay", "paper")):
        return "report"
    if any(w in lower for w in ("project", "prototype", "application")):
        return "project"
    if any(w in lower for w in ("presentation", "pitch")):
        return "presentation"
    return "assignment"


# ---------------------------------------------------------------------------
# Section heading patterns
# ---------------------------------------------------------------------------

_ULO_SECTION_RE = re.compile(
    r"(?:Unit\s+Learning\s+Outcomes?|Learning\s+Outcomes?)\s*\n",
    re.IGNORECASE,
)

_ASSESSMENT_SECTION_RE = re.compile(
    r"(?:Assessment\s+Schedule|Assessment\s+(?:Summary|Overview|Details|Tasks?)"
    r"|Summary\s+of\s+Assessment)\s*\n",
    re.IGNORECASE,
)

_SCHEDULE_SECTION_RE = re.compile(
    r"(?:Program\s+Calendar|Teaching\s+Schedule|Unit\s+Schedule"
    r"|Weekly\s+Schedule|Schedule\s+of\s+Activities)\s*\n",
    re.IGNORECASE,
)

_TEXTBOOK_SECTION_RE = re.compile(
    r"(?:Learning\s+Resources|Prescribed\s+Text|Required\s+Text"
    r"|Textbook|Recommended\s+Reading|Reading\s+List)\s*\n",
    re.IGNORECASE,
)

_DESCRIPTION_SECTION_RE = re.compile(
    r"(?:^|\n)(?:Syllabus|Introduction|Unit\s+Description|Overview)\s*\n",
    re.IGNORECASE,
)

# Metadata patterns
_TITLE_LINE_RE = re.compile(
    r"^([A-Z]{2,6}\d{3,5})\s*(?:\(V\.\d+\)\s*)?(.+)$",
    re.MULTILINE,
)
_UNIT_CODE_RE = re.compile(r"\b([A-Z]{2,6}\d{3,5})\b")
_CREDIT_RE = re.compile(
    r"Credit\s+(?:value|Points?)\s*[:\-]?\s*\n?\s*(\d+)", re.IGNORECASE
)
_SEMESTER_RE = re.compile(r"Semester\s+(\d)\s*,\s*(20\d{2})", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_PREREQ_RE = re.compile(
    r"Pre-?requisite\s+units?\s*:\s*\n?\s*(.+?)(?:\n|$)", re.IGNORECASE
)
_MODE_RE = re.compile(
    r"Mode\s+of\s+study\s*:\s*\n?\s*(\w+)", re.IGNORECASE
)

# Assessment rows: "N\nTitle\nNN %\nWeek:N"
_ASSESS_TASK_RE = re.compile(
    r"(?:^|\n)\s*(\d+)\s*\n"
    r"((?:(?!\d{1,3}\s*%).)+?)\n"
    r"\s*(\d{1,3})\s*%\s*\n"
    r"\s*(?:Week\s*:\s*([\d, ]+))?",
    re.IGNORECASE | re.DOTALL,
)

# Simpler "Title NN%" fallback
_ASSESS_FALLBACK_RE = re.compile(r"(.+?)\s+(\d{1,3})\s*%", re.IGNORECASE)

# Week rows: "Week N: Topic"
_WEEK_ROW_RE = re.compile(
    r"(?:Week|Wk)\s*(\d{1,2})\s*[:\-|]?\s*(.+)", re.IGNORECASE
)

# Numbered ULO: "\n1\nDescription text\n"
_NUMBERED_ITEM_RE = re.compile(r"\n\s*(\d+)\s*\n")

# Textbook: "Author (Year). Title. Publisher."
_TEXTBOOK_ENTRY_RE = re.compile(
    r"([A-Z][a-z]+(?:,\s*[A-Z]\.?\s*(?:[A-Z]\.?\s*)?)?(?:,?\s*&\s*[A-Z]"
    r"[a-z]+(?:,\s*[A-Z]\.?\s*(?:[A-Z]\.?\s*)?)?)*)"
    r"\s*\((\d{4})\)\.\s*"
    r"(.+?)\.\s*"
    r"(.+?)\.",
    re.DOTALL,
)

# All known section headings (used as end markers)
_ALL_SECTIONS: list[re.Pattern[str]] = [
    _ULO_SECTION_RE,
    _ASSESSMENT_SECTION_RE,
    _SCHEDULE_SECTION_RE,
    _TEXTBOOK_SECTION_RE,
    _DESCRIPTION_SECTION_RE,
    re.compile(
        r"(?:Academic\s+Integrity|Special\s+Consideration"
        r"|Referencing\s+Style|Learning\s+Activities"
        r"|Assessment\s+Moderation|Pass\s+requirements"
        r"|Late\s+Assessment|Additional\s+information"
        r"|Graduate\s+Capabilities|Design\s+Philosophy)",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Section extraction helper
# ---------------------------------------------------------------------------


def _section_between(
    text: str, start_re: re.Pattern[str], end_markers: list[re.Pattern[str]]
) -> str | None:
    """Extract text between a start heading and the next known heading."""
    m = start_re.search(text)
    if not m:
        return None
    start = m.end()
    end = len(text)
    for marker in end_markers:
        n = marker.search(text, start)
        if n and n.start() < end:
            end = n.start()
    return text[start:end].strip()


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------


def _extract_metadata(text: str) -> dict[str, str | int | None]:
    """Extract unit code, title, credits, year, semester."""
    result: dict[str, str | int | None] = {}

    title_match = _TITLE_LINE_RE.search(text[:2000])
    if title_match:
        result["unit_code"] = title_match.group(1)
        result["unit_title"] = title_match.group(2).strip()
    else:
        code_match = _UNIT_CODE_RE.search(text[:2000])
        result["unit_code"] = code_match.group(1) if code_match else None
        result["unit_title"] = None

    credit_match = _CREDIT_RE.search(text[:5000])
    result["credit_points"] = (
        int(credit_match.group(1)) if credit_match else None
    )

    sem_match = _SEMESTER_RE.search(text[:3000])
    if sem_match:
        result["semester"] = f"Semester {sem_match.group(1)}"
        result["year"] = int(sem_match.group(2))
    else:
        year_match = _YEAR_RE.search(text[:3000])
        result["year"] = int(year_match.group(1)) if year_match else None
        result["semester"] = None

    prereq_match = _PREREQ_RE.search(text[:5000])
    if prereq_match:
        val = prereq_match.group(1).strip()
        result["prerequisites"] = val if val.lower() != "nil" else None
    else:
        result["prerequisites"] = None

    mode_match = _MODE_RE.search(text[:5000])
    result["delivery_mode"] = (
        mode_match.group(1).strip() if mode_match else None
    )

    return result


def _extract_description(text: str) -> str | None:
    """Extract unit description from Syllabus/Introduction sections."""
    section = _section_between(text, _DESCRIPTION_SECTION_RE, _ALL_SECTIONS)
    if section:
        return section[:2000]
    return None


def _extract_learning_outcomes(text: str) -> list[_LearningOutcome]:
    """Extract ULOs from the Learning Outcomes section."""
    section = _section_between(text, _ULO_SECTION_RE, _ALL_SECTIONS)
    if not section:
        return []

    # Clean preamble
    completion_match = re.search(
        r"On\s+successful\s+completion.*?:", section, re.IGNORECASE
    )
    if completion_match:
        section = section[completion_match.end():]

    section = re.sub(
        r"Graduate\s+Capabilities\s+addressed\s*\n?",
        "", section, flags=re.IGNORECASE,
    )
    section = re.sub(r"GC\d+\s*:[^\n]*\n?", "", section)

    # Split by numbered items
    items = re.split(r"\n\s*(\d+)\s*\n", section)
    outcomes: list[_LearningOutcome] = []
    i = 1
    while i < len(items) - 1:
        num = items[i].strip()
        desc = " ".join(items[i + 1].split()).strip()
        if desc and len(desc) > 5:
            outcomes.append(_LearningOutcome(
                code=f"ULO{num}",
                description=desc[:500],
                bloom_level=_guess_bloom(desc),
            ))
        i += 2

    # Fallback: try "N. Description" pattern
    if not outcomes:
        for m in re.finditer(r"(\d+)\.\s+(.+?)(?=\n\d+\.|$)", section, re.DOTALL):
            desc = " ".join(m.group(2).split()).strip()
            if desc and len(desc) > 5:
                outcomes.append(_LearningOutcome(
                    code=f"ULO{m.group(1)}",
                    description=desc[:500],
                    bloom_level=_guess_bloom(desc),
                ))

    return outcomes


def _extract_assessments(text: str) -> list[_Assessment]:
    """Extract assessments from the Assessment section."""
    section = _section_between(text, _ASSESSMENT_SECTION_RE, _ALL_SECTIONS)
    if not section:
        return []

    assessments: list[_Assessment] = []

    # Try structured pattern
    for m in _ASSESS_TASK_RE.finditer(section):
        title = " ".join(m.group(2).split())
        weight = float(m.group(3))
        due_week_raw = m.group(4)
        due_week: int | None = None
        if due_week_raw:
            first_num = re.search(r"\d+", due_week_raw)
            if first_num:
                due_week = int(first_num.group())
        if title and weight > 0:
            assessments.append(_Assessment(
                title=title,
                weight=weight,
                due_week=due_week,
                category=_guess_category(title),
            ))

    # Fallback: "Title NN%"
    if not assessments:
        for m in _ASSESS_FALLBACK_RE.finditer(section):
            title = m.group(1).strip().rstrip("|").strip()
            weight = float(m.group(2))
            if title and weight > 0 and len(title) > 3:
                due_match = re.search(
                    r"[Ww](?:ee)?k\s*:?\s*(\d{1,2})",
                    section[m.start():m.end() + 150],
                )
                assessments.append(_Assessment(
                    title=title,
                    weight=weight,
                    due_week=int(due_match.group(1)) if due_match else None,
                    category=_guess_category(title),
                ))

    return assessments


def _extract_weekly_schedule(text: str) -> list[_Week]:
    """Extract weekly schedule from the Schedule section."""
    section = _section_between(text, _SCHEDULE_SECTION_RE, _ALL_SECTIONS)
    if not section:
        return []

    weeks: list[_Week] = []

    # Try "Week N: Topic" pattern first
    for m in _WEEK_ROW_RE.finditer(section):
        topic = m.group(2).strip().split("\n")[0].strip()[:300]
        if topic:
            weeks.append(_Week(week_number=int(m.group(1)), topic=topic))

    # Fallback: numbered lines "N\nTopic line"
    if not weeks:
        lines = section.split("\n")
        i = 0
        while i < len(lines) - 1:
            line = lines[i].strip()
            num_match = re.match(r"^(\d{1,2})$", line)
            if num_match:
                week_num = int(num_match.group(1))
                if 1 <= week_num <= 20:
                    # Next non-empty line is the topic
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines):
                        topic = lines[j].strip()[:300]
                        if topic and not re.match(r"^\d{1,2}$", topic):
                            weeks.append(_Week(
                                week_number=week_num, topic=topic
                            ))
            i += 1

    return weeks


def _extract_textbooks(text: str) -> list[_Textbook]:
    """Extract textbooks from the Learning Resources section."""
    section = _section_between(text, _TEXTBOOK_SECTION_RE, _ALL_SECTIONS)
    if not section:
        return []

    textbooks: list[_Textbook] = []

    for m in _TEXTBOOK_ENTRY_RE.finditer(section):
        authors = m.group(1).strip()
        year = m.group(2)
        title = m.group(3).strip()
        publisher = m.group(4).strip()
        title = re.sub(
            r"\s*\(Abbreviated\s+as\s+\w+\)\s*$", "", title
        )
        full_title = f"{authors} ({year}). {title}. {publisher}"

        after = section[m.end():m.end() + 200]
        essential = re.search(
            r"Essential\s*:\s*(Yes|No)", after, re.IGNORECASE
        )
        required = (
            essential.group(1).lower() == "yes" if essential else True
        )
        textbooks.append(_Textbook(
            title=full_title[:300], required=required
        ))

    # Fallback: lines with year in parentheses
    if not textbooks:
        for raw_line in section.split("\n"):
            line = raw_line.strip()
            if len(line) > 30 and re.search(r"\(\d{4}\)", line):
                textbooks.append(_Textbook(title=line[:300]))

    return textbooks


# ---------------------------------------------------------------------------
# Parse raw text into structured outline data
# ---------------------------------------------------------------------------


def _parse_outline(text: str) -> _OutlineData:
    """Parse raw text into structured outline data."""
    metadata = _extract_metadata(text)
    return _OutlineData(
        unit_code=metadata.get("unit_code"),  # type: ignore[arg-type]
        unit_title=metadata.get("unit_title"),  # type: ignore[arg-type]
        description=_extract_description(text),
        credit_points=metadata.get("credit_points"),  # type: ignore[arg-type]
        year=metadata.get("year"),  # type: ignore[arg-type]
        semester=metadata.get("semester"),  # type: ignore[arg-type]
        prerequisites=metadata.get("prerequisites"),  # type: ignore[arg-type]
        delivery_mode=metadata.get("delivery_mode"),  # type: ignore[arg-type]
        learning_outcomes=_extract_learning_outcomes(text),
        weekly_schedule=_extract_weekly_schedule(text),
        assessments=_extract_assessments(text),
        textbooks=_extract_textbooks(text),
        raw_text=text,
    )


# ---------------------------------------------------------------------------
# Format as structured markdown
# ---------------------------------------------------------------------------


def _format_outline(data: _OutlineData) -> str:
    """Format parsed outline data as structured markdown."""
    parts: list[str] = []

    # Header
    title = "Unit Outline"
    if data.unit_code and data.unit_title:
        title = f"Unit Outline: {data.unit_code} {data.unit_title}"
    elif data.unit_code:
        title = f"Unit Outline: {data.unit_code}"
    parts.append(f"# {title}")

    # Metadata
    meta_lines: list[str] = []
    if data.credit_points:
        meta_lines.append(f"- **Credit Points:** {data.credit_points}")
    if data.year and data.semester:
        meta_lines.append(f"- **Period:** {data.semester}, {data.year}")
    elif data.year:
        meta_lines.append(f"- **Year:** {data.year}")
    if data.delivery_mode:
        meta_lines.append(f"- **Mode:** {data.delivery_mode}")
    if data.prerequisites:
        meta_lines.append(f"- **Prerequisites:** {data.prerequisites}")
    if meta_lines:
        parts.append("\n".join(meta_lines))

    # Description
    if data.description:
        parts.append(f"## Description\n\n{data.description}")

    # Assessments
    if data.assessments:
        lines = ["## Assessments\n"]
        for a in data.assessments:
            due = f" — Due Week {a.due_week}" if a.due_week else ""
            lines.append(
                f"- **{a.title}** ({a.category}) — {a.weight:.0f}%{due}"
            )
        parts.append("\n".join(lines))

    # Weekly Schedule
    if data.weekly_schedule:
        lines = ["## Weekly Schedule\n"]
        for w in sorted(data.weekly_schedule, key=lambda x: x.week_number):
            lines.append(f"- **Week {w.week_number}:** {w.topic}")
            for act in w.activities:
                lines.append(f"  - {act}")
        parts.append("\n".join(lines))

    # Learning Outcomes
    if data.learning_outcomes:
        lines = ["## Learning Outcomes\n"]
        for lo in data.learning_outcomes:
            lines.append(
                f"- **{lo.code}:** {lo.description} "
                f"({lo.bloom_level.capitalize()})"
            )
        parts.append("\n".join(lines))

    # Textbooks
    if data.textbooks:
        lines = ["## Textbooks\n"]
        for tb in data.textbooks:
            req = "Required" if tb.required else "Recommended"
            lines.append(f"- {tb.title} [{req}]")
        parts.append("\n".join(lines))

    # If we extracted nothing structured, include the raw text
    has_structure = (
        data.assessments
        or data.weekly_schedule
        or data.learning_outcomes
    )
    if not has_structure:
        parts.append(
            "## Full Text\n\n" + data.raw_text[:10000]
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_unit_outline(file_path: str) -> str:
    """Extract structured text from a unit outline document (DOCX or PDF).

    Takes an absolute path to a DOCX/PDF unit outline.
    Returns structured markdown with clearly labeled sections
    (assessments, schedule, learning outcomes, textbooks).
    Falls back to raw text if no structure is detected.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".docx":
        from botstash.extractors.docx import extract_docx
        raw_text = extract_docx(path)
    elif suffix == ".pdf":
        from botstash.extractors.pdf import extract_pdf
        raw_text = extract_pdf(path)
    else:
        msg = f"Unsupported unit outline format: {suffix}"
        raise ValueError(msg)

    data = _parse_outline(raw_text)
    return _format_outline(data)
