"""Tests for the BotStash WebUI."""

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from botstash.webui.app import create_app


def test_upload_page() -> None:
    """GET / returns the upload form."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Upload Course Content" in response.text
    assert "course_zip" in response.text


def test_extract_flow(tmp_path: Path) -> None:
    """POST /extract processes uploads and shows review page."""
    app = create_app()
    client = TestClient(app)

    # Build a minimal IMSCC ZIP
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n"
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

    course_zip = tmp_path / "course.zip"
    with zipfile.ZipFile(course_zip, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("intro.vtt", vtt)

    # Build a transcripts ZIP
    trans_zip = tmp_path / "transcripts.zip"
    with zipfile.ZipFile(trans_zip, "w") as zf:
        zf.writestr(
            "Lecture_1.vtt",
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nContent\n",
        )

    with open(course_zip, "rb") as cz, open(trans_zip, "rb") as tz:
        response = client.post(
            "/extract",
            files={
                "course_zip": ("course.zip", cz, "application/zip"),
                "transcripts_zip": ("trans.zip", tz, "application/zip"),
            },
        )

    assert response.status_code == 200
    assert "Review Extracted Content" in response.text
    assert "Intro" in response.text
