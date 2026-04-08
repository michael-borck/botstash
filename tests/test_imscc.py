"""Tests for IMSCC ingestion."""

import zipfile
from pathlib import Path

from botstash.ingester.imscc import extract_imscc


def _build_imscc(tmp_path: Path, resources: dict[str, str]) -> Path:
    """Build a minimal IMSCC ZIP with a manifest and resource files."""
    manifest_resources = ""
    manifest_items = ""
    for i, (href, _content) in enumerate(resources.items()):
        rid = f"res_{i}"
        manifest_resources += (
            f'  <resource identifier="{rid}" type="webcontent" href="{href}">\n'
            f'    <file href="{href}"/>\n'
            f"  </resource>\n"
        )
        title = Path(href).stem.replace("_", " ")
        manifest_items += (
            f'  <item identifier="item_{i}" identifierref="{rid}">\n'
            f"    <title>{title}</title>\n"
            f"  </item>\n"
        )

    manifest = f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1">
  <organizations>
    <organization>
{manifest_items}
    </organization>
  </organizations>
  <resources>
{manifest_resources}
  </resources>
</manifest>"""

    zip_path = tmp_path / "course.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        for href, content in resources.items():
            zf.writestr(href, content)
    return zip_path


def test_extract_imscc_webcontent(tmp_path: Path) -> None:
    """Extracts text from webcontent resources."""
    vtt_content = (
        "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello from VTT\n"
    )
    zip_path = _build_imscc(tmp_path, {"lecture.vtt": vtt_content})

    records = extract_imscc(zip_path)
    assert len(records) == 1
    assert "Hello from VTT" in records[0].extracted_text
    assert records[0].file_type == ".vtt"
    assert records[0].title == "lecture"


def test_extract_imscc_html_with_urls(tmp_path: Path) -> None:
    """Extracts URLs from HTML content and logs them."""
    html = '<a href="https://echo360.org/video/123">Watch Lecture</a>'
    zip_path = _build_imscc(tmp_path, {"page.html": html})
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    records = extract_imscc(zip_path, output_dir=output_dir)
    # Short HTML with URL should become a video_url record
    assert any(r.file_type == "url" for r in records)
    # URL log should be written
    log_file = output_dir / "urls_log.txt"
    assert log_file.exists()
    assert "echo360.org" in log_file.read_text()


def test_extract_imscc_no_manifest(tmp_path: Path) -> None:
    """Returns empty list when no manifest is found."""
    zip_path = tmp_path / "empty.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "No manifest here")

    records = extract_imscc(zip_path)
    assert records == []


def test_extract_imscc_unsupported_files(tmp_path: Path) -> None:
    """Skips files with no registered extractor."""
    zip_path = _build_imscc(tmp_path, {"data.csv": "a,b,c\n1,2,3"})
    records = extract_imscc(zip_path)
    assert records == []
