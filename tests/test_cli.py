"""Tests for CLI commands using Click's CliRunner."""

from pathlib import Path

from click.testing import CliRunner

from botstash.cli import cli


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "botstash" in result.output
    assert "0.1.1" in result.output


def test_extract_command(tmp_path: Path) -> None:
    """Extract command scans a folder."""
    runner = CliRunner()

    # Create a folder with a VTT file
    content = tmp_path / "course"
    content.mkdir()
    (content / "Lecture_1.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nContent\n"
    )

    output = tmp_path / "staging"
    result = runner.invoke(cli, [
        "extract",
        str(content),
        "--output", str(output),
    ])
    assert result.exit_code == 0
    assert "Extracted" in result.output
    assert (output / "tags.json").exists()


def test_extract_no_recursive(tmp_path: Path) -> None:
    """Extract with --no-recursive skips subdirectories."""
    runner = CliRunner()

    content = tmp_path / "course"
    content.mkdir()
    sub = content / "week1"
    sub.mkdir()
    (content / "top.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nTop\n"
    )
    (sub / "deep.vtt").write_text(
        "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nDeep\n"
    )

    output = tmp_path / "staging"
    result = runner.invoke(cli, [
        "extract",
        str(content),
        "--output", str(output),
        "--no-recursive",
    ])
    assert result.exit_code == 0
    assert "Extracted 1 items" in result.output


def test_init_command(tmp_path: Path) -> None:
    """Init command scaffolds .botstash.env with all settings."""
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli, ["init"],
            input="http://localhost:3001\nmy-api-key\nn\ny\n",
        )
        assert result.exit_code == 0
        env_path = Path(".botstash.env")
        assert env_path.exists()
        content = env_path.read_text()
        assert "ANYTHINGLLM_URL=http://localhost:3001" in content
        assert "ANYTHINGLLM_KEY=my-api-key" in content
        assert "INCLUDE_ANSWERS=false" in content
        assert "RECURSIVE=true" in content
