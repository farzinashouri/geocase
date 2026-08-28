"""Gates for the generated catalog schematics.

The class of bug these exist to catch: card anchors are *raw HTML*, so mkdocs
does not rewrite ``.md`` targets inside them the way it does for Markdown
links, and ``mkdocs build --strict`` does not validate href attributes in raw
HTML either. A wrong prefix there ships broken links that nothing else notices
-- which is exactly how Batch 5's 187 broken links happened.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
GENERATED = REPO_ROOT / "docs" / "_generated" / "catalog"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# mypy cannot see scripts/ (it is outside the gated `mypy src` scope), so the
# sys.path import above is invisible to it.
from catalog_geometry import (  # type: ignore[import-not-found] # noqa: E402
    geometry_provider,
)
from catalog_svg import (  # type: ignore[import-not-found] # noqa: E402
    case_diagram,
    case_thumbnail,
)

sys.path.insert(0, str(REPO_ROOT / "src"))

from geocase import load_case  # noqa: E402
from geocase.catalog.registry import get_registry  # noqa: E402


@pytest.fixture(scope="module")
def cases() -> list:
    return list(get_registry().list_cases())


def _category(case) -> str:
    return str(getattr(case.category, "value", case.category))


def test_every_vector_case_has_a_schematic(cases: list) -> None:
    """Vector cases all declare a geometry type, so all must draw."""
    missing = [
        case.id
        for case in cases
        if _category(case) == "vector" and not case_thumbnail(case)
    ]
    assert missing == [], f"vector cases with no schematic: {missing}"


def test_schematics_use_theme_variables_not_hex(cases: list) -> None:
    """A hard-coded colour would strand the diagram in one Material scheme."""
    for case in cases:
        svg = case_thumbnail(case)
        if svg:
            assert "#" not in svg, f"{case.id} hard-codes a colour"


def test_schematics_are_labelled(cases: list) -> None:
    """The diagrams carry information, so they need an accessible name."""
    for case in cases:
        svg = case_thumbnail(case)
        if svg:
            assert 'role="img"' in svg and "aria-label=" in svg, case.id


def test_caption_declares_the_metadata_provenance(cases: list) -> None:
    """With no geometry provider every diagram must disclaim being the real data."""
    for case in cases:
        figure = "".join(case_diagram(case))
        if figure:
            assert "Schematic" in figure, case.id
            assert "not the fixture" in figure or "not from the pixels" in figure, (
                case.id
            )


def _provider():
    """A provider matching the one ``generate_catalog_pages.py`` wires in."""
    return geometry_provider(lambda cid: load_case(cid).load())


def _thumbnail_with_preview(case_id: str) -> str:
    """Render a thumbnail through the real-geometry provider, as the generator does."""
    case = get_registry().get(case_id)
    return case_thumbnail(case, geometry_provider=_provider())


def test_distinct_polygons_render_distinct_paths() -> None:
    """Two different polygons must not share one hardcoded archetype drawing."""
    pytest.importorskip("geopandas")
    simple = _thumbnail_with_preview("simple_valid_polygon")
    dateline = _thumbnail_with_preview("dateline_crossing_polygon")
    bowtie = _thumbnail_with_preview("self_intersecting_polygon")

    assert simple and dateline and bowtie
    assert simple != dateline
    assert simple != bowtie
    assert dateline != bowtie


def test_preview_reflects_real_coordinate_extent() -> None:
    """``simple_valid_polygon`` is a unit square; its path must be closed and square."""
    pytest.importorskip("geopandas")
    svg = _thumbnail_with_preview("simple_valid_polygon")

    paths = re.findall(r'<path d="([^"]+)"', svg)
    assert paths, "expected a real geometry path"
    d = paths[0]
    assert d.endswith("Z"), d

    coords = [
        (float(x), float(y)) for x, y in re.findall(r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)", d)
    ]
    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    assert span_x > 0 and span_y > 0
    assert abs(span_x / span_y - 1.0) < 0.05, (span_x, span_y)


def test_caption_matches_render_path() -> None:
    """The caption must say which path was taken -- real geometry or fallback."""
    pytest.importorskip("geopandas")
    provider = _provider()
    registry = get_registry()

    real = "".join(
        case_diagram(registry.get("simple_valid_polygon"), geometry_provider=provider)
    )
    assert "actual geometry" in real
    assert "Schematic only" not in real

    # ``unclosed_ring_polygon`` is deliberately malformed and cannot load.
    fallback = "".join(
        case_diagram(registry.get("unclosed_ring_polygon"), geometry_provider=provider)
    )
    assert "Schematic only" in fallback
    assert "actual geometry" not in fallback


def test_compare_page_lists_every_case(cases: list) -> None:
    """The compare page must cover the whole corpus, not a filtered slice."""
    page = GENERATED / "compare.md"
    assert page.exists(), "docs/_generated/catalog/compare.md is not generated"

    text = page.read_text(encoding="utf-8")
    ids = set(re.findall(r'data-case-id="([^"]+)"', text))
    missing = sorted({case.id for case in cases} - ids)
    assert missing == [], f"cases missing from the compare page: {missing}"


def test_compare_page_links_resolve() -> None:
    """Raw-HTML row hrefs bypass mkdocs link rewriting, so they need their own gate."""
    page = GENERATED / "compare.md"
    text = page.read_text(encoding="utf-8")

    hrefs = re.findall(r'class="gc-compare-link" href="([^"]+)"', text)
    assert hrefs, "compare page has no case links"

    offenders = [href for href in hrefs if ".md" in href]
    assert offenders == [], f"compare links must not use .md targets: {offenders}"

    case_dir = GENERATED / "cases"
    broken = [
        href
        for href in hrefs
        if not (case_dir / f"{href.rstrip('/').rsplit('/', 1)[-1]}.md").exists()
    ]
    assert broken == [], f"compare links with no target page: {broken}"


def test_generated_card_links_have_no_markdown_targets() -> None:
    """Raw-HTML card hrefs must be resolved URLs, never ``.md`` paths."""
    offenders: list[str] = []
    for page in GENERATED.rglob("*.md"):
        for line in page.read_text(encoding="utf-8").splitlines():
            if 'class="gc-card"' in line and ".md" in line:
                offenders.append(f"{page.relative_to(REPO_ROOT)}: {line.strip()}")
    assert offenders == [], "card links must not use .md targets:\n" + "\n".join(
        offenders
    )


def test_generated_card_links_resolve_to_real_case_pages() -> None:
    """Each card must point at a case page that exists on disk."""
    case_dir = GENERATED / "cases"
    broken: list[str] = []
    for page in GENERATED.rglob("*.md"):
        for href in re.findall(
            r'class="gc-card" href="([^"]+)"', page.read_text(encoding="utf-8")
        ):
            case_id = href.rstrip("/").rsplit("/", 1)[-1]
            if not (case_dir / f"{case_id}.md").exists():
                broken.append(f"{page.relative_to(REPO_ROOT)} -> {href}")
    assert broken == [], "card links with no target page:\n" + "\n".join(broken)
