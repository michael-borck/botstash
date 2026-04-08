"""Tests for the two-pass heuristic classifier."""

from pathlib import Path

from botstash.classifier.auto import (
    _classify_by_content,
    _classify_by_filename,
    _derive_title,
    _extract_week,
    _safe_filename,
    classify,
)
from botstash.models import ResourceRecord, read_tags


def test_pass1_lecture() -> None:
    assert _classify_by_filename("Week3_Lecture_Slides.pptx") == "lecture"


def test_pass1_worksheet() -> None:
    assert _classify_by_filename("Lab_Worksheet_5.docx") == "worksheet"


def test_pass1_assignment() -> None:
    assert _classify_by_filename("Assignment1_Brief.pdf") == "assignment"


def test_pass1_rubric() -> None:
    assert _classify_by_filename("marking_criteria.docx") == "rubric"


def test_pass1_no_match() -> None:
    assert _classify_by_filename("random_notes.txt") is None


def test_pass2_vtt() -> None:
    assert _classify_by_content("any text", ".vtt") == "transcript"


def test_pass2_url() -> None:
    assert _classify_by_content("https://example.com", "url") == "video_url"


def test_pass2_qti_namespace() -> None:
    text = '<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">'
    assert _classify_by_content(text, ".xml") == "quiz"


def test_pass2_unit_outline_single_signal() -> None:
    """Single signal is not enough for unit_outline."""
    text = "This unit covers... Learning Outcomes: 1. Understand..."
    assert _classify_by_content(text, ".docx") is None


def test_pass2_unit_outline_multiple_signals() -> None:
    """Two+ structural signals → unit_outline."""
    text = (
        "Learning Outcomes\n"
        "1. Explain the role of IS\n"
        "Assessment Schedule\n"
        "Assignment 1 30%\n"
    )
    assert _classify_by_content(text, ".docx") == "unit_outline"


def test_pass2_unit_outline_three_signals() -> None:
    """Three signals → high confidence unit_outline."""
    text = (
        "Credit Points: 25\n"
        "Learning Outcomes\n"
        "Weekly Schedule\n"
        "Week 1: Introduction\n"
    )
    assert _classify_by_content(text, ".pdf") == "unit_outline"


def test_pass2_no_match() -> None:
    assert _classify_by_content("Generic text content here", ".docx") is None


def test_pass2_overrides_pass1() -> None:
    """Content heuristic (quiz) overrides filename heuristic (lecture)."""
    records = [
        ResourceRecord(
            source_file="Week1_Lecture_Quiz.xml",
            extracted_text='<questestinterop xmlns="http://www.imsglobal.org/xsd/ims_qtiasiv1p2">',
            file_type=".xml",
            title="Week 1 Quiz",
        ),
    ]
    tags = classify(records, Path("/tmp/test_classify"))
    assert tags[0].type == "quiz"


def test_extract_week_from_filename() -> None:
    assert _extract_week("Week3_Lecture.pptx", "") == 3


def test_extract_week_from_text() -> None:
    assert _extract_week("slides.pptx", "Welcome to Week 5 of the course") == 5


def test_extract_week_none() -> None:
    assert _extract_week("Assignment1.docx", "No week info here") is None


def test_derive_title() -> None:
    assert _derive_title("Week1_Intro_Slides.pptx") == "Week1 Intro Slides"


def test_derive_title_hyphens() -> None:
    assert _derive_title("lab-worksheet-3.docx") == "Lab Worksheet 3"


def test_classify_writes_files(tmp_path: Path) -> None:
    """Classify writes text files and tags.json to output_dir."""
    records = [
        ResourceRecord(
            source_file="Week1_Lecture.pptx",
            extracted_text="Slide content here",
            file_type=".pptx",
            title="Week 1 Lecture",
        ),
        ResourceRecord(
            source_file="transcript.vtt",
            extracted_text="Hello from the lecture",
            file_type=".vtt",
            title="Lecture Transcript",
        ),
    ]

    classify(records, tmp_path / "staging")
    staging = tmp_path / "staging"

    # Check text files written
    assert (staging / "Week1_Lecture.txt").exists()
    assert (staging / "transcript.txt").exists()

    # Check tags.json
    assert (staging / "tags.json").exists()
    loaded = read_tags(staging / "tags.json")
    assert len(loaded) == 2
    assert loaded[0].type == "lecture"
    assert loaded[0].week == 1
    assert loaded[1].type == "transcript"


def test_classify_fallback_misc(tmp_path: Path) -> None:
    """Unknown content falls back to misc type."""
    records = [
        ResourceRecord(
            source_file="random_data.csv",
            extracted_text="a,b,c\n1,2,3",
            file_type=".csv",
            title="Some Data",
        ),
    ]
    tags = classify(records, tmp_path / "staging")
    assert tags[0].type == "misc"


def test_safe_filename_no_collision() -> None:
    """Unique filenames pass through unchanged."""
    used: set[str] = set()
    assert _safe_filename("lecture.pptx", used) == "lecture.txt"
    assert _safe_filename("notes.docx", used) == "notes.txt"


def test_safe_filename_collision() -> None:
    """Colliding filenames get a hash suffix."""
    used: set[str] = set()
    name1 = _safe_filename("folder1/slides.pptx", used)
    name2 = _safe_filename("folder2/slides.pptx", used)
    assert name1 == "slides.txt"
    assert name2 != "slides.txt"
    assert name2.startswith("slides_")
    assert name2.endswith(".txt")


def test_classify_filename_collision(tmp_path: Path) -> None:
    """Files with same stem from different paths don't overwrite."""
    records = [
        ResourceRecord(
            source_file="week1/notes.docx",
            extracted_text="Week 1 notes",
            file_type=".docx",
            title="Week 1 Notes",
        ),
        ResourceRecord(
            source_file="week2/notes.docx",
            extracted_text="Week 2 notes",
            file_type=".docx",
            title="Week 2 Notes",
        ),
    ]
    tags = classify(records, tmp_path / "staging")
    assert len(tags) == 2
    # Both files should exist with different names
    paths = {Path(t.extracted_as).name for t in tags}
    assert len(paths) == 2  # no collision
