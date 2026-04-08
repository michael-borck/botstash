"""Tests for the folder scanner."""

import zipfile
from pathlib import Path

from botstash.pipeline import scan_folder


def _make_vtt(path: Path, text: str) -> None:
    path.write_text(
        f"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n{text}\n"
    )


def test_scan_mixed_files(tmp_path: Path) -> None:
    """Scans a folder with VTT and other files."""
    _make_vtt(tmp_path / "lecture.vtt", "Hello from lecture")
    (tmp_path / "notes.txt").write_text("Not extractable")

    records = scan_folder(tmp_path)
    assert len(records) == 1
    assert records[0].file_type == ".vtt"
    assert "Hello from lecture" in records[0].extracted_text


def test_scan_recursive(tmp_path: Path) -> None:
    """Recursively finds files in subdirectories."""
    sub = tmp_path / "week1"
    sub.mkdir()
    _make_vtt(sub / "lecture.vtt", "Week 1 content")
    _make_vtt(tmp_path / "intro.vtt", "Intro content")

    records = scan_folder(tmp_path, recursive=True)
    assert len(records) == 2


def test_scan_non_recursive(tmp_path: Path) -> None:
    """Non-recursive only gets top-level files."""
    sub = tmp_path / "week1"
    sub.mkdir()
    _make_vtt(sub / "lecture.vtt", "Week 1 content")
    _make_vtt(tmp_path / "intro.vtt", "Intro content")

    records = scan_folder(tmp_path, recursive=False)
    assert len(records) == 1
    assert "Intro content" in records[0].extracted_text


def test_scan_plain_zip(tmp_path: Path) -> None:
    """Unzips non-IMSCC ZIPs and processes contents."""
    # Create a ZIP with a VTT file
    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nZipped content\n"
    zip_path = tmp_path / "content.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("lecture.vtt", vtt_content)

    records = scan_folder(tmp_path)
    assert len(records) == 1
    assert "Zipped content" in records[0].extracted_text


def test_scan_imscc_zip(tmp_path: Path) -> None:
    """Detects IMSCC ZIP and uses manifest parser."""
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1">
  <organizations><organization>
    <item identifier="i0" identifierref="r0">
      <title>Intro Lecture</title>
    </item>
  </organization></organizations>
  <resources>
    <resource identifier="r0" type="webcontent" href="intro.vtt">
      <file href="intro.vtt"/>
    </resource>
  </resources>
</manifest>"""
    zip_path = tmp_path / "course.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("intro.vtt", vtt)

    records = scan_folder(tmp_path)
    assert len(records) >= 1
    assert any("Hello" in r.extracted_text for r in records)


def test_scan_nested_zip(tmp_path: Path) -> None:
    """Handles nested ZIPs (ZIP inside ZIP)."""
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nNested content\n"

    # Create inner ZIP
    inner_zip_path = tmp_path / "inner.zip"
    with zipfile.ZipFile(inner_zip_path, "w") as zf:
        zf.writestr("deep.vtt", vtt)

    # Create outer ZIP containing inner ZIP
    outer_zip_path = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer_zip_path, "w") as zf:
        zf.write(inner_zip_path, "inner.zip")

    # Remove inner zip from folder (only outer should be scanned)
    inner_zip_path.unlink()

    records = scan_folder(tmp_path)
    assert len(records) == 1
    assert "Nested content" in records[0].extracted_text


def test_scan_skips_unsupported(tmp_path: Path) -> None:
    """Silently skips unsupported file types."""
    (tmp_path / "data.csv").write_text("a,b,c")
    (tmp_path / "image.png").write_bytes(b"\x89PNG")

    records = scan_folder(tmp_path)
    assert records == []


def test_scan_empty_folder(tmp_path: Path) -> None:
    """Returns empty list for empty folder."""
    records = scan_folder(tmp_path)
    assert records == []


def test_scan_qti_xml(tmp_path: Path) -> None:
    """Extracts QTI XML files found in folder."""
    qti = """<?xml version="1.0" encoding="UTF-8"?>
    <questestinterop>
      <assessment><section><item>
        <presentation>
          <mattext>What is 2 + 2?</mattext>
        </presentation>
      </item></section></assessment>
    </questestinterop>"""
    (tmp_path / "quiz.xml").write_text(qti)

    records = scan_folder(tmp_path)
    assert len(records) == 1
    assert "2 + 2" in records[0].extracted_text


def test_scan_non_qti_xml_skipped(tmp_path: Path) -> None:
    """Non-QTI XML files are skipped (no questions extracted)."""
    (tmp_path / "config.xml").write_text(
        '<?xml version="1.0"?><config><setting>value</setting></config>'
    )
    records = scan_folder(tmp_path)
    assert records == []
