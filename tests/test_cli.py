"""Tests for CLI commands using Click's CliRunner."""

import zipfile
from pathlib import Path

from click.testing import CliRunner

from botstash.cli import cli


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "botstash" in result.output
    assert "0.1.0" in result.output


def test_extract_command(tmp_path: Path) -> None:
    """Extract command processes IMSCC + transcripts."""
    runner = CliRunner()

    # Build minimal IMSCC
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
    zip_path = tmp_path / "course.imscc"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("imsmanifest.xml", manifest)
        zf.writestr("intro.vtt", vtt)

    # Create transcripts dir
    transcripts = tmp_path / "transcripts"
    transcripts.mkdir()
    (transcripts / "Lecture_1.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nContent\n"
    )

    output = tmp_path / "staging"
    result = runner.invoke(cli, [
        "extract",
        str(zip_path),
        str(transcripts),
        "--output", str(output),
    ])
    assert result.exit_code == 0
    assert "Extracted" in result.output
    assert (output / "tags.json").exists()


def test_init_command(tmp_path: Path) -> None:
    """Init command scaffolds .botstash.env."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli, ["init"],
            input="http://localhost:3001\nmy-api-key\n",
        )
        assert result.exit_code == 0
        env_path = Path(".botstash.env")
        assert env_path.exists()
        content = env_path.read_text()
        assert "ANYTHINGLLM_URL=http://localhost:3001" in content
        assert "ANYTHINGLLM_KEY=my-api-key" in content
