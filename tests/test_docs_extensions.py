"""Tests for the extensions API reference documentation source.

These tests verify that the docs source registers every extension class so the
Sphinx ``autosummary`` table in ``docs/api/extensions.rst`` lists each extension,
and that each extension appears in the narrative Extensions section of
``docs/api.rst``.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
API_RST = ROOT / "docs" / "api.rst"
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


def _section_lines(path: pathlib.Path, heading: str) -> list[str]:
    """Return the body lines of the section whose heading is ``heading``.

    A section is a heading line followed by a dashed underline. The body ends at
    the next dashed underline (the start of the following section).
    """
    lines = path.read_text().splitlines()
    for i in range(len(lines) - 1):
        if lines[i].strip() == heading and set(lines[i + 1].strip()) == {"-"}:
            body: list[str] = []
            for line in lines[i + 2 :]:
                if line.strip() and set(line.strip()) == {"-"}:
                    break
                body.append(line)
            return body
    raise AssertionError(f"Section {heading!r} not found in {path}")


def _mod_references(lines: list[str]) -> list[str]:
    """Extract the module paths targeted by ``:mod:`...<path>``` roles."""
    refs: list[str] = []
    for line in lines:
        refs.extend(re.findall(r":mod:`[^`]+<([^>]+)>`", line))
    return refs


def test_embeddings_extension_is_in_api_index_extensions() -> None:
    """The embeddings extension must be listed in the Extensions section of api.rst."""
    section = _section_lines(API_RST, "Extensions")
    assert "pystac.extensions.embeddings" in _mod_references(section)
