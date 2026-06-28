"""Basic smoke tests."""

from importlib.metadata import version

from botstash import __version__


def test_version() -> None:
    # Derived from installed package metadata, not a literal, so this test
    # never needs editing when the version is bumped.
    assert __version__ == version("botstash")
