"""Tests for the pipeline orchestration."""

import zipfile
from pathlib import Path

from botstash.models import read_tags
from botstash.pipeline import run_extract


def _make_vtt(path: Path, text: str) -> None:
    path.write_text(
        f"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n{text}\n"
    )


def test_run_extract_folder(tmp_path: Path) -> None:
    """Extract pipeline scans a folder with mixed content."""
    # Create a folder with VTT files and an IMSCC ZIP
    content = tmp_path / "course"
    content.mkdir()

    _make_vtt(content / "Week_1_Lecture.vtt", "Lecture content")
    _make_vtt(content / "Week_2_Tutorial.vtt", "Tutorial content")

    # Add an IMSCC ZIP
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nFrom IMSCC\n"
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1">
  <organizations><organization>
    <item identifier="i0" identifierref="r0">
      <title>Intro</title>
    </item>
  </organization></organizations>
  <resources>
    <resource identifier="r0" type="webcontent" href="intro.vtt">
      <file href="intro.vtt"/>
    </resource>
  </resources>
</manifest>"""
    zip_path = content / "export.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("intro.vtt", vtt)

    # Run pipeline
    output_dir = tmp_path / "staging"
    tags = run_extract(content, output_dir)

    # Should find: 2 loose VTT + 1 from IMSCC = 3
    assert len(tags) >= 3
    assert (output_dir / "tags.json").exists()

    loaded = read_tags(output_dir / "tags.json")
    assert len(loaded) == len(tags)

    types = {t.type for t in tags}
    assert "transcript" in types


def test_run_extract_non_recursive(tmp_path: Path) -> None:
    """Non-recursive extract only processes top-level."""
    content = tmp_path / "course"
    content.mkdir()
    sub = content / "week1"
    sub.mkdir()

    _make_vtt(content / "intro.vtt", "Top level")
    _make_vtt(sub / "deep.vtt", "Nested")

    output_dir = tmp_path / "staging"
    tags = run_extract(content, output_dir, recursive=False)
    assert len(tags) == 1
