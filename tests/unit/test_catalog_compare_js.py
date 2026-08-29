"""Source-text gates for the compare page's progressive-enhancement script.

The behaviour itself needs a browser, which this suite does not have. What can
be gated here is the *contract*: that the script still binds the two halves of
the page together, and that it stays dependency-free (plan 31's no-CDN rule).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "docs" / "javascripts" / "catalog-compare.js"


def test_compare_js_binds_map_to_table() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "gc-worldmap" in source, "the script no longer reaches into the map"
    assert "caseId" in source
    assert "scrollIntoView" in source
    assert "gc-row-highlight" in source


def test_compare_js_loads_nothing_from_the_network() -> None:
    """No CDN, no bundler: the docs build ships neither."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "http" not in source, "compare script references an external URL"
