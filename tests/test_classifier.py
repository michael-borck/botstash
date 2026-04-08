"""Tests for the two-pass heuristic classifier."""

from pathlib import Path

from botstash.classifier.auto import (
    _classify_by_content,
    _classify_by_filename,
    _derive_title,
    _extract_week,
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


def test_pass2_unit_outline() -> None:
    text = "This unit covers... Learning Outcomes: 1. Understand..."
    assert _classify_by_content(text, ".docx") == "unit_outline"


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
