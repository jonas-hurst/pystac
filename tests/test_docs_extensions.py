"""Tests for the extensions API reference documentation source.

These tests verify that the docs source registers every extension class so the
Sphinx ``autosummary`` table in ``docs/api/extensions.rst`` lists each extension.
"""

import pathlib

ROOT = pathlib.Path(__file__).parent.parent
EXTENSIONS_RST = ROOT / "docs" / "api" / "extensions.rst"


def _autosummary_entries(path: pathlib.Path) -> list[str]:
    """Return the indented entries listed under ``.. autosummary::``."""
    text = path.read_text()
    marker = ".. autosummary::"
    start = text.index(marker) + len(marker)
    entries: list[str] = []
    started = False
    for line in text[start:].splitlines():
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if stripped.startswith(".."):
            continue
        started = True
        entries.append(stripped)
    return entries


def test_embeddings_extension_is_in_extensions_autosummary() -> None:
    """The EmbeddingsExtension must be listed in the extensions autosummary."""
    entries = _autosummary_entries(EXTENSIONS_RST)
    assert "embeddings.EmbeddingsExtension" in entries
