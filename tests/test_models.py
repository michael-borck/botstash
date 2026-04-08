"""Tests for shared data models."""

from pathlib import Path

from botstash.models import TagEntry, read_tags, write_tags


def test_tags_roundtrip(tmp_path: Path) -> None:
    """Tags serialize to JSON and deserialize back correctly."""
    tags = [
        TagEntry(
            source_file="Week1_Intro.pptx",
            extracted_as="staging/Week1_Intro.txt",
            type="lecture",
            title="Week 1: Introduction",
            week=1,
        ),
        TagEntry(
            source_file="Rubric.docx",
            extracted_as="staging/Rubric.txt",
            type="rubric",
            title="Assessment Rubric",
            week=None,
        ),
    ]
    tags_path = tmp_path / "tags.json"
    write_tags(tags, tags_path)
    loaded = read_tags(tags_path)

    assert len(loaded) == 2
    assert loaded[0].source_file == "Week1_Intro.pptx"
    assert loaded[0].week == 1
    assert loaded[1].type == "rubric"
    assert loaded[1].week is None
