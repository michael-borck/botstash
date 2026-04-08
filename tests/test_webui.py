"""Tests for the BotStash WebUI."""

import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from botstash.webui.app import create_app


def test_upload_page() -> None:
    """GET / returns the upload form with single file input."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Upload Course Content" in response.text
    assert "content_zip" in response.text
    assert "include_answers" in response.text
    assert "recursive" in response.text


def test_extract_flow(tmp_path: Path) -> None:
    """POST /extract with single ZIP shows review page."""
    app = create_app()
    client = TestClient(app)

    # Build a ZIP with mixed content
    content_zip = tmp_path / "content.zip"
    with zipfile.ZipFile(content_zip, "w") as zf:
        zf.writestr(
            "Lecture_1.vtt",
            "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n",
        )

    with open(content_zip, "rb") as f:
        response = client.post(
            "/extract",
            files={
                "content_zip": ("content.zip", f, "application/zip"),
            },
        )

    assert response.status_code == 200
    assert "Review Extracted Content" in response.text
