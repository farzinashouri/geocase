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


def test_compare_js_suppresses_the_native_title() -> None:
    """Two tooltips per hover is one too many; the HTML one is the keeper.

    The generator's ``<title>`` is the no-JS fallback, so it stays in the SVG.
    When the script runs it removes the element -- otherwise the browser draws
    its own tooltip on top of the styled one -- and moves the text to
    ``aria-label`` so the accessible name survives the removal.
    """
    source = SCRIPT.read_text(encoding="utf-8")

    assert "aria-label" in source, (
        "removing <title> without an aria-label drops the accessible name"
    )
    assert "removeChild" in source or "remove()" in source, (
        "the native <title> is never removed, so both tooltips still show"
    )


def test_footprints_are_clickable() -> None:
    """Everything on the map that names a case filters to it.

    This reverses Plan 33's split affordance, which made the footprint --
    the *largest* target on the map, and the one a reader aims at first --
    the one thing that did nothing when pressed. A polygon and the marker
    over it stand for the same case, so they perform the same action; the
    original "mixed affordance" objection was really about a footprint that
    *navigated away*, not about one that filters like everything else.
    """
    source = SCRIPT.read_text(encoding="utf-8")
    region = _clickable_region(source)

    assert 'role", "button"' in source or "role='button'" in source, (
        "map targets must announce themselves as pressable"
    )
    assert "data-case-id]" in region, (
        "footprints are outside the clickable branch, so they cannot filter"
    )


def test_every_marker_is_clickable() -> None:
    """Filtering to one row is a real action, so a lone marker filters too.

    A reader who has just filtered by a cluster and then clicks its neighbour
    reads a dead marker as broken, not as a considered omission.
    """
    region = _clickable_region(SCRIPT.read_text(encoding="utf-8"))

    assert "if (!isCluster)" not in region, (
        "a single-case marker is still short-circuited out of the click path"
    )
    assert 'node.style.cursor = "default"' not in region, (
        "single-case markers still override the pointer cursor"
    )


def _clickable_region(source: str) -> str:
    """The part of the script that attaches click/keydown handlers."""
    start = source.find("CLICKABLE-START")
    end = source.find("CLICKABLE-END")
    assert start != -1 and end != -1, (
        "the clickable branch must be delimited so this gate can find it"
    )
    return source[start:end]


def test_footprints_get_a_pointer_cursor() -> None:
    """They filter now, so they must look like they do.

    Not ``help``: the question-mark cursor promised a native tooltip that
    barely worked, and it is the styled one that answers the hover.
    """
    css = STYLES.read_text(encoding="utf-8")

    block = re.search(r"\.gc-map-extent-group\s*\{([^}]*)\}", css)
    assert block, "the footprint rule is gone"
    assert "cursor: pointer" in block.group(1), (
        "footprints are clickable but do not show a pointer"
    )
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


def test_the_map_root_title_is_suppressed_too() -> None:
    """The ``<svg>`` root carries a ``<title>``, and it was the one left behind.

    ``world_map()`` titles the root element -- "Vector coverage: where 91
    cases sit on Earth" -- as the map's no-JS accessible name. The
    suppression loop originally queried only ``[data-case-id]`` and
    ``[data-case-ids]``, so it stripped every footprint and marker title and
    left the root's in place. A native ``<title>`` applies to the whole
    subtree, so the root's took over as soon as the child titles were gone:
    hovering *any* part of the map, including a footprint, raised the
    browser's own tooltip after its delay, on top of the styled one that had
    been up since the pointer arrived. The root gets the same treatment as
    its children -- text to ``aria-label``, element removed.
    """
    source = SCRIPT.read_text(encoding="utf-8")

    selector = re.search(
        r'document\.querySelectorAll\(\s*"([^"]*gc-worldmap[^"]*)"', source
    )
    assert selector is not None, "the title-suppression query is gone"
    assert ".gc-worldmap," in selector.group(1).replace(" ", ""), (
        "the suppression selector never matches the .gc-worldmap root itself, "
        "so the root <title> survives and the browser draws it over the "
        "styled tooltip"
    )
