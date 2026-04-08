"""Tests for configuration loading."""

from pathlib import Path

from botstash.config import _parse_bool, load_config


def _clean_env(monkeypatch: object) -> None:
    """Remove all botstash-related env vars."""
    for var in ("ANYTHINGLLM_URL", "ANYTHINGLLM_KEY", "INCLUDE_ANSWERS", "RECURSIVE"):
        monkeypatch.delenv(var, raising=False)  # type: ignore[attr-defined]


def test_load_from_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Config loads from .botstash.env file."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text(
        "ANYTHINGLLM_URL=https://test.example.com\n"
        "ANYTHINGLLM_KEY=testkey123\n"
    )
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)

    config = load_config()
    assert config.url == "https://test.example.com"
    assert config.key == "testkey123"


def test_env_var_overrides_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Environment variables take priority over dotenv file."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text("ANYTHINGLLM_URL=https://dotenv.example.com\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)
    monkeypatch.setenv("ANYTHINGLLM_URL", "https://envvar.example.com")  # type: ignore[attr-defined]

    config = load_config()
    assert config.url == "https://envvar.example.com"


def test_cli_arg_overrides_all(tmp_path: Path, monkeypatch: object) -> None:
    """CLI arguments take highest priority."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)
    monkeypatch.setenv("ANYTHINGLLM_URL", "https://envvar.example.com")  # type: ignore[attr-defined]

    config = load_config(url_override="https://cli.example.com")
    assert config.url == "https://cli.example.com"


def test_returns_none_when_no_config(tmp_path: Path, monkeypatch: object) -> None:
    """Returns None values when no config is available."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)

    config = load_config()
    assert config.url is None
    assert config.key is None


def test_boolean_defaults(tmp_path: Path, monkeypatch: object) -> None:
    """Boolean settings have correct defaults."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)

    config = load_config()
    assert config.include_answers is False
    assert config.recursive is True


def test_boolean_from_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Boolean settings load from dotenv."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text("INCLUDE_ANSWERS=true\nRECURSIVE=false\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)

    config = load_config()
    assert config.include_answers is True
    assert config.recursive is False


def test_boolean_env_var_overrides_dotenv(tmp_path: Path, monkeypatch: object) -> None:
    """Env vars override dotenv for booleans."""
    env_file = tmp_path / ".botstash.env"
    env_file.write_text("INCLUDE_ANSWERS=false\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)
    monkeypatch.setenv("INCLUDE_ANSWERS", "true")  # type: ignore[attr-defined]

    config = load_config()
    assert config.include_answers is True


def test_boolean_cli_overrides_all(tmp_path: Path, monkeypatch: object) -> None:
    """CLI override takes priority for booleans."""
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    _clean_env(monkeypatch)
    monkeypatch.setenv("INCLUDE_ANSWERS", "true")  # type: ignore[attr-defined]

    config = load_config(include_answers_override=False)
    assert config.include_answers is False


def test_parse_bool_values() -> None:
    """Bool parser handles various string formats."""
    assert _parse_bool("true", False) is True
    assert _parse_bool("True", False) is True
    assert _parse_bool("1", False) is True
    assert _parse_bool("yes", False) is True
    assert _parse_bool("false", True) is False
    assert _parse_bool("0", True) is False
    assert _parse_bool("no", True) is False
    assert _parse_bool(None, True) is True
    assert _parse_bool(None, False) is False
