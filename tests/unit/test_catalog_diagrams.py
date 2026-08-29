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

    # compare.md is served at /catalog/compare/, its own directory, so a href
    # is resolved against that -- not against the catalog root the source file
    # sits in. Checking only the basename would have passed the ``cases/<id>/``
    # links that actually resolved to /catalog/compare/cases/<id>/.
    wrong_depth = [href for href in hrefs if not href.startswith("../cases/")]
    assert wrong_depth == [], (
        f"compare links must be relative to /catalog/compare/: {wrong_depth}"
    )

    case_dir = GENERATED / "cases"
    broken = [
        href
        for href in hrefs
        if not (case_dir / f"{href.rstrip('/').rsplit('/', 1)[-1]}.md").exists()
    ]
    assert broken == [], f"compare links with no target page: {broken}"


def test_compare_page_previews_resolve() -> None:
    """Preview ``<img>`` sources are raw HTML too, so they need the same gate."""
    page = GENERATED / "compare.md"
    text = page.read_text(encoding="utf-8")

    sources = re.findall(r'class="gc-diagram gc-preview" src="([^"]+)"', text)
    assert sources, "compare page has no raster previews"

    previews = GENERATED / "previews"
    broken = [
        src
        for src in sources
        if not src.startswith("../previews/")
        or not (previews / src.rsplit("/", 1)[-1]).exists()
    ]
    assert broken == [], f"compare previews with no target file: {broken}"


def test_case_page_previews_resolve() -> None:
    """Case pages render two levels below the catalog root; their srcs must say so."""
    previews = GENERATED / "previews"
    broken: list[str] = []
    for page in (GENERATED / "cases").glob("*.md"):
        for src in re.findall(
            r'class="gc-diagram gc-preview" src="([^"]+)"',
            page.read_text(encoding="utf-8"),
        ):
            if (
                not src.startswith("../../previews/")
                or not (previews / src.rsplit("/", 1)[-1]).exists()
            ):
                broken.append(f"{page.name} -> {src}")
    assert broken == [], "case-page previews with no target file:\n" + "\n".join(broken)


def _preview_url(case_id: str) -> str:
    """A preview-URL provider matching the one the generator wires in."""
    return f"previews/{case_id}.png"


def test_raster_pages_embed_the_pixel_preview() -> None:
    """A shaped raster case must show its pixels, not only the band schematic."""
    case = get_registry().get("optical_rgb_small")
    figure = "".join(case_diagram(case, preview_url_provider=_preview_url))
    assert 'src="previews/optical_rgb_small.png"' in figure
    assert "actual pixels" in figure


def test_unshaped_raster_gets_no_preview() -> None:
    """No declared shape means no preview, whatever the provider answers.

    The provider here answers for *every* id, which is the failure mode this
    guards: the diagram must select on the case's own metadata rather than
    trusting a URL to exist, or a page ends up with a broken image.

    The case is built here rather than drawn from the registry because every
    bundled raster now declares ``expected_shape`` -- the catalog no longer
    supplies an unshaped example, but the selection rule still has to hold for
    external and manifest-supplied cases that may omit it.
    """
    case = get_registry().get("optical_rgb_small").model_copy(deep=True)
    case.assertions.expected_shape = None

    figure = "".join(case_diagram(case, preview_url_provider=_preview_url))
    assert "<img" not in figure


def test_raster_preview_is_labelled() -> None:
    """The image carries information, so it needs alt text like the SVGs do."""
    case = get_registry().get("optical_rgb_small")
    rendered = case_thumbnail(case, preview_url_provider=_preview_url)
    assert "alt=" in rendered and 'alt=""' not in rendered


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


# --- Plan 31: geography on the pages ----------------------------------------


def test_case_pages_state_where_the_case_is(cases: list) -> None:
    """A CRS is a coordinate convention; a reader needs a location.

    Every bundled case declares a region, and all but four resolve to an
    extent, so the Location row is not optional decoration -- its absence
    means the generator dropped the field.
    """
    missing = []
    for case in cases:
        if case.region is None and case.extent is None:
            continue
        page = GENERATED / "cases" / f"{case.id}.md"
        if not page.exists():
            continue
        if "Location" not in page.read_text(encoding="utf-8"):
            missing.append(case.id)
    assert missing == [], f"case pages with no Location row: {missing}"


def test_dateline_page_shows_a_wrapped_extent() -> None:
    """The case exists to demonstrate the wrap, so the page must show it."""
    page = GENERATED / "cases" / "dateline_crossing_polygon.md"
    text = page.read_text(encoding="utf-8")

    assert "Location" in text
    assert "antimeridian" in text.lower(), "the wrap must be called out in words"
    # The naive envelope, which is the bug this case is about.
    assert "-180" not in text.split("## Notes")[0]


def test_json_ld_carries_a_geoshape_box() -> None:
    """schema.org understands a box; it understands nothing about a CRS string."""
    import json as _json

    page = GENERATED / "cases" / "simple_valid_polygon.md"
    text = page.read_text(encoding="utf-8")
    blob = text.split('<script type="application/ld+json">')[1].split("</script>")[0]
    payload = _json.loads(blob)

    coverage = payload["spatialCoverage"]
    assert coverage["@type"] == "Place"
    assert coverage["geo"]["@type"] == "GeoShape"
    # "south west north east", the schema.org GeoShape ordering.
    assert coverage["geo"]["box"] == "50.0 10.0 51.0 11.0"


def test_compare_page_carries_both_world_maps() -> None:
    """One map would pile 130 markers onto two synthetic points -- hence two."""
    text = (GENERATED / "compare.md").read_text(encoding="utf-8")

    assert 'class="gc-worldmap"' in text
    assert text.count('class="gc-worldmap"') == 2, "expected a vector and a raster map"
    assert "Vector coverage" in text
    assert "Raster coverage" in text
    assert "gc-map-marker" in text, "the maps must plot the cases"


def test_world_maps_use_theme_variables_not_hex() -> None:
    """Same rule as the schematics: a hex literal strands the map in one scheme."""
    from catalog_svg import world_map  # type: ignore[import-not-found]

    registry_cases = [case for case in get_registry().list_cases() if case.extent]
    svg = world_map(registry_cases, "All cases")

    assert svg
    assert "#" not in svg, "world map hard-codes a colour"


def test_world_map_clusters_colocated_cases() -> None:
    """23 rasters share one transform; 23 stacked dots would be unreadable."""
    from catalog_svg import world_map  # type: ignore[import-not-found]

    rasters = [
        case
        for case in get_registry().list_cases()
        if _category(case) == "raster" and case.extent
    ]
    svg = world_map(rasters, "Raster coverage")

    markers = svg.count("gc-map-marker")
    assert markers < len(rasters), (
        f"{len(rasters)} raster cases produced {markers} markers -- "
        "co-located cases must collapse into one marker with a count"
    )
    assert "gc-map-count" in svg, "a cluster must show how many cases it holds"


def test_world_map_draws_a_wrapping_extent_against_both_edges() -> None:
    """An antimeridian box is two rectangles, one per edge -- never one wide one."""
    from catalog_svg import world_map  # type: ignore[import-not-found]

    dateline = get_registry().get("dateline_crossing_polygon")
    svg = world_map([dateline], "Antimeridian")

    # The class attribute specifically -- ``--gc-map-extent`` is also the name
    # of the CSS variable the rectangles are filled with.
    assert svg.count('class="gc-map-extent"') == 2, svg


def test_world_map_extent_rects_carry_case_identity() -> None:
    """A footprint a reader cannot name is a footprint they cannot use."""
    from catalog_svg import world_map  # type: ignore[import-not-found]

    dateline = get_registry().get("dateline_crossing_polygon")
    svg = world_map([dateline], "Antimeridian")

    # Identity is per-box: the antimeridian split makes two rects for one case,
    # and both must answer "what am I?".
    assert svg.count('data-case-id="dateline_crossing_polygon"') == 2, svg
    assert "dateline_crossing_polygon -- Dateline crossing polygon" in svg


def test_world_map_marks_pole_caps_distinctly() -> None:
    """A pole cap's 180-degree band is bbox arithmetic, not the data's shape."""
    from catalog_svg import world_map  # type: ignore[import-not-found]

    north = get_registry().get("north_pole_polygon")
    svg = world_map([north], "Polar")

    assert 'class="gc-map-extent gc-map-polar"' in svg, svg
    title = svg[svg.index("<title>", svg.index("gc-map-extent-group")) :]
    title = title[: title.index("</title>")].lower()
    assert "pole" in title and "bounding box" in title, title


def test_pole_cap_is_detected_from_extent_not_declared() -> None:
    """Derived from the extent, so it cannot drift from what it describes."""
    from catalog_svg import _is_pole_cap  # type: ignore[import-not-found]

    from geocase.catalog.models import SpatialExtent

    assert _is_pole_cap(SpatialExtent(west=-90, south=84, east=90, north=89.5))
    assert not _is_pole_cap(SpatialExtent(west=-90, south=-3, east=90, north=3))
    assert not _is_pole_cap(get_registry().get("dateline_crossing_polygon").extent)


def test_compare_map_and_table_share_case_ids() -> None:
    """Guards the JS binding contract at generation time, not in a browser."""
    text = (GENERATED / "compare.md").read_text(encoding="utf-8")

    rows = set(re.findall(r'<tr[^>]*data-case-id="([^"]+)"', text))
    assert rows, "compare table carries no data-case-id rows"

    for svg in re.findall(r'<svg class="gc-worldmap".*?</svg>', text, re.S):
        for case_id in re.findall(r'data-case-id="([^"]+)"', svg):
            assert case_id in rows, f"map plots {case_id} with no matching table row"
        for group in re.findall(r'data-case-ids="([^"]+)"', svg):
            for case_id in group.split():
                assert case_id in rows, f"cluster names {case_id} with no row"


def test_thumbnail_decimates_a_dense_geometry() -> None:
    """A 4096-vertex path would bloat compare.md past text-diffability."""
    from catalog_svg import (  # type: ignore[import-not-found]
        _MAX_THUMBNAIL_POINTS,
        _decimate,
    )

    dense = [(float(i), float(i % 7)) for i in range(4096)]
    thinned = _decimate(dense)

    assert len(thinned) <= _MAX_THUMBNAIL_POINTS
    assert thinned[0] == dense[0]
    assert thinned[-1] == dense[-1], "decimation must keep the ring closed"
    assert _decimate(dense[:50]) == dense[:50], "short rings must pass through"
