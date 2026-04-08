"""Tests for configuration loading."""

from pathlib import Path

from botstash.config import load_config


def test_load_from_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Config loads from .botstash.env file."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text("ANYTHINGLLM_URL=https://test.example.com\nANYTHINGLLM_KEY=testkey123\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    monkeypatch.delenv("ANYTHINGLLM_URL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("ANYTHINGLLM_KEY", raising=False)  # type: ignore[attr-defined]

    config = load_config()
    assert config.url == "https://test.example.com"
    assert config.key == "testkey123"


def test_env_var_overrides_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Environment variables take priority over dotenv file."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text("ANYTHINGLLM_URL=https://dotenv.example.com\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setenv("ANYTHINGLLM_URL", "https://envvar.example.com")  # type: ignore[attr-defined]
    monkeypatch.delenv("ANYTHINGLLM_KEY", raising=False)  # type: ignore[attr-defined]

    config = load_config()
    assert config.url == "https://envvar.example.com"


def test_cli_arg_overrides_all(tmp_path: Path, monkeypatch: object) -> None:
    """CLI arguments take highest priority."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    monkeypatch.setenv("ANYTHINGLLM_URL", "https://envvar.example.com")  # type: ignore[attr-defined]

    config = load_config(url_override="https://cli.example.com")
    assert config.url == "https://cli.example.com"


def test_returns_none_when_no_config(tmp_path: Path, monkeypatch: object) -> None:
    """Returns None values when no config is available."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    monkeypatch.delenv("ANYTHINGLLM_URL", raising=False)  # type: ignore[attr-defined]
    monkeypatch.delenv("ANYTHINGLLM_KEY", raising=False)  # type: ignore[attr-defined]

    config = load_config()
    assert config.url is None
    assert config.key is None
