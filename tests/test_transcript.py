"""Tests for VTT transcript ingestion."""

from pathlib import Path

from botstash.ingester.transcript import ingest_transcripts


def _make_vtt(path: Path, text: str) -> None:
    path.write_text(
        f"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n{text}\n"
    )


def test_ingest_transcripts(tmp_path: Path) -> None:
    """Ingests all VTT files from a folder."""
    _make_vtt(tmp_path / "Week_1_Lecture.vtt", "First lecture content")
    _make_vtt(tmp_path / "Week_2_Lecture.vtt", "Second lecture content")

    records = ingest_transcripts(tmp_path)
    assert len(records) == 2
    assert records[0].source_file == "Week_1_Lecture.vtt"
    assert records[0].file_type == ".vtt"
    assert records[0].title == "Week 1 Lecture"
    assert "First lecture content" in records[0].extracted_text


def test_ingest_empty_folder(tmp_path: Path) -> None:
    """Returns empty list for folder with no VTT files."""
    records = ingest_transcripts(tmp_path)
    assert records == []


def test_ignores_non_vtt(tmp_path: Path) -> None:
    """Ignores non-VTT files in the folder."""
    _make_vtt(tmp_path / "lecture.vtt", "Real content")
    (tmp_path / "notes.txt").write_text("Not a VTT file")

    records = ingest_transcripts(tmp_path)
    assert len(records) == 1
