"""Tests for the pipeline orchestration."""

import zipfile
from pathlib import Path

from botstash.models import read_tags
from botstash.pipeline import run_extract


def _make_vtt(path: Path, text: str) -> None:
    path.write_text(
        f"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n{text}\n"
    )


def _make_imscc(tmp_path: Path) -> Path:
    """Build a minimal IMSCC ZIP."""
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nCourse intro\n"
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1">
  <organizations>
    <organization>
      <item identifier="item_0" identifierref="res_0">
        <title>Week 1 Lecture Recording</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="res_0" type="webcontent" href="lecture.vtt">
      <file href="lecture.vtt"/>
    </resource>
  </resources>
</manifest>"""
    zip_path = tmp_path / "course.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("lecture.vtt", vtt)
    return zip_path


def test_run_extract(tmp_path: Path) -> None:
    """Full extract pipeline produces tags.json."""
    # Set up IMSCC
    zip_path = _make_imscc(tmp_path)

    # Set up transcripts folder
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    _make_vtt(transcripts / "Week_2_Tutorial.vtt", "Tutorial content")

    # Run pipeline
    output_dir = tmp_path / "staging"
    tags = run_extract(zip_path, transcripts, output_dir)

    # Verify
    assert len(tags) >= 2
    assert (output_dir / "tags.json").exists()

    # Check we can read back
    loaded = read_tags(output_dir / "tags.json")
    assert len(loaded) == len(tags)

    # Check types are assigned
    types = {t.type for t in tags}
    assert "transcript" in types  # VTT files
