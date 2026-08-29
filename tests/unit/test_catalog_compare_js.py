"""Source-text gates for the compare page's progressive-enhancement script.

The behaviour itself needs a browser, which this suite does not have. What can
be gated here is the *contract*: that the script still binds the two halves of
the page together, that it stays dependency-free (plan 31's no-CDN rule), and
that the two kinds of map element keep the *different* affordances they are
supposed to have.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "docs" / "javascripts" / "catalog-compare.js"
STYLES = REPO_ROOT / "docs" / "stylesheets" / "catalog.css"


def test_compare_js_binds_map_to_table() -> None:
    source = SCRIPT.read_text(encoding="utf-8")

    assert "gc-worldmap" in source, "the script no longer reaches into the map"
    assert "caseId" in source
    assert "gc-row-highlight" in source


def test_compare_js_loads_nothing_from_the_network() -> None:
    """No CDN, no bundler: the docs build ships neither."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "http" not in source, "compare script references an external URL"


def test_compare_js_builds_an_html_tooltip() -> None:
    """A native <title> waits ~1s and truncates; the point is to read it fast."""
    source = SCRIPT.read_text(encoding="utf-8")

    assert "gc-map-tooltip" in source, "no HTML tooltip element is built"
    # The tooltip has to be positioned against the pointer, or it renders in
    # the corner of the page rather than next to what it describes.
    assert "clientX" in source and "clientY" in source


def test_only_clusters_are_clickable() -> None:
    """Footprints are read, not pressed -- the mixed affordance was the bug.

    A ``help`` cursor says "hover me" and ``role="button"`` says "click me".
    Putting both on one element is what made clicking a footprint feel like a
    misfire, so the click affordance now belongs to cluster markers alone.
    """
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'role", "button"' in source or "role='button'" in source, (
        "clusters must still announce themselves as pressable"
    )
    # The selector that gets the click handlers must not pick up footprints.
    assert "gc-map-extent-group" not in _clickable_region(source), (
        "footprints are inside the clickable branch again"
    )


def _clickable_region(source: str) -> str:
    """The part of the script that attaches click/keydown handlers."""
    start = source.find("CLICKABLE-START")
    end = source.find("CLICKABLE-END")
    assert start != -1 and end != -1, (
        "the clickable branch must be delimited so this gate can find it"
    )
    return source[start:end]


def test_footprints_do_not_get_a_help_cursor() -> None:
    """The question-mark cursor was promising a native tooltip that barely worked."""
    css = STYLES.read_text(encoding="utf-8")

    block = re.search(r"\.gc-map-extent-group\s*\{([^}]*)\}", css)
    assert block, "the footprint rule is gone"
    assert "cursor: help" not in block.group(1), (
        "footprints still claim the help cursor"
    )


def test_clusters_get_a_pointer_cursor() -> None:
    """They are clickable now, so they must look clickable."""
    css = STYLES.read_text(encoding="utf-8")

    block = re.search(r"\.gc-map-marker\s*\{([^}]*)\}", css)
    assert block, "the marker rule is gone"
    assert "cursor: pointer" in block.group(1), (
        "clusters are clickable but do not show a pointer"
    )
