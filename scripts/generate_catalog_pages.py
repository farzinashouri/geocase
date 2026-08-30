"""Generate the public catalog pages for the documentation site.

Reads every registered case through the catalog registry and emits, under
``docs/_generated/catalog/``:

- ``index.md``            -- catalog landing page with grouped listings,
- ``cases/<case_id>.md``  -- one page per case, with ``schema.org/Dataset`` JSON-LD,
- ``risk/<slug>.md``      -- hub page per risk type,
- ``format/<slug>.md``    -- hub page per format.

The per-case pages carry the JSON-LD that makes the catalog eligible for
Google Dataset Search, so they are the main SEO surface of the site.

Use ``--check`` in CI to assert the committed output is up to date.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
OUTPUT_ROOT = REPO_ROOT / "docs" / "_generated" / "catalog"

# The GitHub Pages project URL is the catalog's single public, canonical home.
# Override with GEOCASE_SITE_URL (or --site-url) only as part of a deliberate
# migration, then regenerate so every JSON-LD URL changes together.
DEFAULT_SITE_URL = os.environ.get(
    "GEOCASE_SITE_URL", "https://farzinashouri.github.io/geocase"
)

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from geocase.catalog.registry import get_registry  # noqa: E402
from geocase.catalog.roots import case_roots_by_id  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_geometry import geometry_provider  # noqa: E402
from catalog_svg import case_diagram, case_thumbnail, world_map  # noqa: E402


def _build_geometry_provider() -> Any:
    """Return a cached provider of loaded case geometry, or ``None``.

    ``None`` means the geospatial stack is unavailable, and every vector
    diagram falls back to its metadata archetype with the caption saying so.
    The ``catalog`` CI job installs ``.[raster,vector]``, so the real path is
    the one that runs in the gate.
    """
    try:
        import geocase
    except ImportError:  # pragma: no cover - only hit in a bare checkout
        return None
    return geometry_provider(lambda case_id: geocase.load_case(case_id).load())


#: Built once per run so each case is loaded at most once, however many pages
#: draw it.
GEOMETRY_PROVIDER = _build_geometry_provider()

#: Directory the raster pixel previews are generated into, relative to
#: ``OUTPUT_ROOT``. ``generate_raster_previews.py`` writes it; this module only
#: links at it, so a missing preview shows up as the gate failing there rather
#: than as a silently image-less page here.
PREVIEW_DIR = "previews"


def _preview_urls(prefix: str) -> Any:
    """Return a preview-URL provider for pages sitting at ``prefix`` levels up.

    The URL must be relative to the *rendered* page, not to the markdown file:
    mkdocs serves ``cases/foo.md`` at ``/catalog/cases/foo/``, so a case page
    is two levels below the catalog root even though its source file is one.
    """

    def provide(case_id: str) -> str | None:
        return f"{prefix}{PREVIEW_DIR}/{case_id}.png"

    return provide


#: Vector cases that cannot be loaded fall back to an archetype, which is
#: correct for the few deliberately-malformed fixtures but catastrophic if it
#: happens to all of them. A run without geopandas would degrade *every* vector
#: page silently and commit the result, so anything past this many fallbacks is
#: treated as a broken environment rather than as broken fixtures.
MAX_VECTOR_FALLBACKS = 10


# Descriptions are written for contributors, not searchers. Until they are
# rewritten, fall back through the richer prose fields before using the title.
DESCRIPTION_FIELDS = ("description", "behavioral_goal", "title")

MAX_META_DESCRIPTION = 155
MAX_RELATED_CASES = 5

# Most risk types apply to a single case. A hub page listing one row is thin
# content, so those risks stay unlinked and are surfaced on the case page and
# the catalog index instead.
MIN_HUB_CASES = 2


def _value(field: Any) -> str:
    """Return the plain string for a field that may be an enum."""
    if field is None:
        return ""
    return str(getattr(field, "value", field))


def _slug(text: str) -> str:
    """Return a URL-safe slug for a tag, risk type, or format name."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return slug.strip("-")


def _collapse(text: str) -> str:
    """Collapse whitespace so prose fits on a single front-matter line."""
    return " ".join(text.split())


def _meta_description(case: Any) -> str:
    """Build the SEO meta description for a case page."""
    for field in DESCRIPTION_FIELDS:
        raw = getattr(case, field, None)
        if raw:
            text = _collapse(str(raw))
            if len(text) <= MAX_META_DESCRIPTION:
                return text
            return text[: MAX_META_DESCRIPTION - 1].rstrip() + "…"
    return f"GeoCase test case {case.id}."


def _yaml_quote(text: str) -> str:
    """Quote a string for safe use as a YAML front-matter scalar."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _front_matter(title: str, description: str) -> list[str]:
    return [
        "---",
        f"title: {_yaml_quote(title)}",
        f"description: {_yaml_quote(description)}",
        "---",
        "",
    ]


def _generated_note() -> list[str]:
    return [
        "<!-- Generated by scripts/generate_catalog_pages.py. Do not edit by hand. -->",
        "",
    ]


def _format_degrees(value: float, axis: str) -> str:
    """Render one coordinate with a hemisphere letter, not a signed number.

    ``-170.0`` is correct and unreadable; ``170.00W`` is the form a reader can
    place without doing arithmetic in their head.
    """
    positive, negative = ("E", "W") if axis == "lon" else ("N", "S")
    hemisphere = positive if value >= 0 else negative
    return f"{abs(value):.2f}&deg;{hemisphere}"


def _format_extent(extent: Any) -> str:
    """Render an extent as a corner-to-corner span, naming a wrap explicitly.

    The wrap has to be said in words. Four numbers where west is larger than
    east look like a typo unless the page says what they mean, and this is
    the one fact the antimeridian cases exist to teach.
    """
    corner_sw = (
        f"{_format_degrees(extent.west, 'lon')}, {_format_degrees(extent.south, 'lat')}"
    )
    corner_ne = (
        f"{_format_degrees(extent.east, 'lon')}, {_format_degrees(extent.north, 'lat')}"
    )
    span = f"{corner_sw} &rarr; {corner_ne}"
    if extent.crosses_antimeridian:
        span += (
            " (crosses the antimeridian &mdash; the box runs east from the "
            "first corner, over 180&deg;)"
        )
    return span


def _location_value(case: Any) -> str | None:
    """The Location row's value: the region label, the extent, or both."""
    region = getattr(case, "region", None)
    extent = getattr(case, "extent", None)
    if extent is not None:
        formatted = _format_extent(extent)
        return f"{region} &mdash; {formatted}" if region else formatted
    return region


def _attribute_rows(case: Any) -> list[tuple[str, str]]:
    """Return the (label, value) pairs shown in the case summary table."""
    rows: list[tuple[str, str]] = [
        ("Case ID", f"`{case.id}`"),
        ("Category", _value(case.category)),
        ("Format", _value(case.format)),
    ]
    if case.geometry_type:
        rows.append(("Geometry type", _value(case.geometry_type)))
    if case.crs:
        rows.append(("CRS", f"`{case.crs}`"))
    # A CRS is a coordinate convention, not a location: two cases sharing
    # EPSG:4326 can be on opposite sides of the planet. This is the row that
    # actually says where the data is.
    location = _location_value(case)
    if location:
        rows.append(("Location", location))
    rows.extend(
        [
            ("Test tier", _value(case.test_tier)),
            ("Size class", _value(case.size_class)),
            ("Storage class", _value(case.storage_class)),
            ("Redistributable", "yes" if case.redistributable else "no"),
            ("Loader", f"`{_value(case.loader_hint)}`"),
        ]
    )
    status = getattr(case, "status", None)
    if status:
        rows.append(("Status", _value(status)))
    return rows


def _badges(case: Any) -> list[str]:
    """Render the case's defining facts as chips under the page title.

    These duplicate rows in the property table by design: the table is a
    reference a reader scans once, the badges are the identity of the page.
    """
    bits = [_value(case.category), _value(case.format)]
    if case.geometry_type:
        bits.append(_value(case.geometry_type))
    if case.crs:
        bits.append(case.crs)
    bits.append(_value(case.size_class))
    bits.append(_value(case.storage_class))

    chips = "".join(f'<span class="gc-badge">{bit}</span>' for bit in bits if bit)
    return ['<div class="gc-badges">', chips, "</div>", ""]


def _case_card(case: Any, href: str, preview_urls: Any) -> list[str]:
    """Render one case as a thumbnail card for a grid listing."""
    meta = _value(case.format)
    geom = _value(case.geometry_type)
    if geom:
        meta = f"{meta} &middot; {geom}"
    return [
        f'<a class="gc-card" href="{href}">',
        case_thumbnail(case, GEOMETRY_PROVIDER, preview_urls),
        f'<span class="gc-card-title">{case.title}</span>',
        f'<span class="gc-card-meta">{meta}</span>',
        "</a>",
    ]


def _case_grid(cases: list[Any], href_prefix: str, preview_prefix: str) -> list[str]:
    """Render a grid of case cards, skipping cases with no drawable schematic.

    ``href_prefix`` must be a *resolved* URL prefix, not a Markdown path.
    These anchors are raw HTML, so mkdocs does not rewrite ``.md`` targets
    inside them the way it does for Markdown links -- emitting ``foo.md`` here
    ships a broken link that ``mkdocs build --strict`` will not catch.
    """
    preview_urls = _preview_urls(preview_prefix)
    cards: list[str] = []
    for case in cases:
        if not case_thumbnail(case, GEOMETRY_PROVIDER, preview_urls):
            continue
        cards.extend(_case_card(case, f"{href_prefix}{case.id}/", preview_urls))
    if not cards:
        return []
    return ['<div class="gc-grid">', *cards, "</div>", ""]


def _required_drivers_cell(drivers: list[str]) -> str:
    """Render ``required_drivers`` as prose an OGR consumer can act on.

    The empty-string sentinel (``NO_OGR_DRIVER``) would otherwise render as an
    empty pair of backticks, which tells the reader nothing. It carries the
    most useful sentence on the page for a WKB/WKT case, so it gets words.
    """
    if not drivers:
        return ""
    if drivers == [""]:
        return "none &mdash; no OGR driver opens this format (use shapely)"
    return ", ".join(f"`{driver}`" for driver in drivers if driver)


def _assertion_rows(case: Any) -> list[tuple[str, str]]:
    """Return the populated assertion hints as (label, value) pairs."""
    assertions = getattr(case, "assertions", None)
    if assertions is None:
        return []

    dumped = assertions.model_dump(exclude_none=True)
    rows: list[tuple[str, str]] = []
    for key, value in dumped.items():
        if key == "required_drivers":
            rendered = _required_drivers_cell(value)
            if not rendered:
                continue
            rows.append((f"`{key}`", rendered))
            continue
        if isinstance(value, list):
            if not value:
                continue
            if all(isinstance(item, int) for item in value):
                # Shapes and band counts read better as a single literal.
                rendered = f"`{list(value)}`"
            else:
                rendered = ", ".join(f"`{item}`" for item in value)
        elif isinstance(value, bool):
            rendered = "yes" if value else "no"
        else:
            rendered = f"`{_value(value)}`"
        rows.append((f"`{key}`", rendered))
    return rows


def _table(headers: tuple[str, str], rows: list[tuple[str, str]]) -> list[str]:
    lines = [f"| {headers[0]} | {headers[1]} |", "|---|---|"]
    lines.extend(f"| {left} | {right} |" for left, right in rows)
    return lines


def _related_cases(case: Any, all_cases: list[Any]) -> list[Any]:
    """Return cases sharing the most tags and risk types with ``case``."""
    own_tags = set(case.tags)
    own_risks = set(case.risk_types)

    scored: list[tuple[int, str, Any]] = []
    for other in all_cases:
        if other.id == case.id:
            continue
        # Risk overlap is the stronger signal: it is what a reader browsing one
        # failure mode actually wants to see next.
        score = 2 * len(own_risks & set(other.risk_types)) + len(
            own_tags & set(other.tags)
        )
        if _value(other.category) == _value(case.category):
            score += 1
        if score > 0:
            scored.append((-score, other.id, other))

    scored.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in scored[:MAX_RELATED_CASES]]


def _json_ld(case: Any, site_url: str) -> list[str]:
    """Build the schema.org/Dataset JSON-LD block for a case page."""
    case_url = f"{site_url}/_generated/catalog/cases/{case.id}/"
    source = getattr(case, "source", None)

    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": case.title,
        "description": _collapse(
            str(case.description or case.behavioral_goal or case.title)
        ),
        "identifier": case.id,
        "url": case_url,
        "isPartOf": {
            "@type": "DataCatalog",
            "name": "GeoCase",
            "url": site_url,
        },
    }

    keywords = sorted(set(case.tags) | set(case.risk_types))
    if keywords:
        payload["keywords"] = keywords

    if source is not None:
        if source.license:
            payload["license"] = source.license
        if source.name:
            payload["creator"] = {"@type": "Organization", "name": source.name}
        if source.url:
            payload["isBasedOn"] = source.url

    primary = getattr(case.files, "primary", None)
    if primary:
        payload["distribution"] = [
            {
                "@type": "DataDownload",
                "encodingFormat": _value(case.format),
                "name": primary,
            }
        ]

    place: dict[str, Any] = {}
    if case.crs:
        place["additionalProperty"] = {
            "@type": "PropertyValue",
            "name": "coordinateReferenceSystem",
            "value": case.crs,
        }
    extent = getattr(case, "extent", None)
    if extent is not None:
        # schema.org GeoShape.box is "south west north east", space separated,
        # in WGS84. This is the SEO payoff: a search engine understands a box
        # and understands nothing whatsoever about an EPSG string.
        place["geo"] = {
            "@type": "GeoShape",
            "box": (f"{extent.south} {extent.west} {extent.north} {extent.east}"),
        }
    region = getattr(case, "region", None)
    if region:
        place["name"] = region
    if place:
        payload["spatialCoverage"] = {"@type": "Place", **place}

    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    return ['<script type="application/ld+json">', rendered, "</script>", ""]


#: Heading levels are shifted by this much when notes are inlined, so the notes'
#: own ``##`` sections nest under the page's ``## Notes`` rather than competing
#: with the page's structure.
_NOTES_HEADING_SHIFT = 1

#: Deepest heading Markdown defines. Anything that would shift past it is left
#: at ``######`` rather than emitted as invalid syntax.
_MAX_HEADING_LEVEL = 6


def _notes_body(case_dir: Path, notes_name: str) -> list[str]:
    """Return the case's ``notes.md`` body, ready to nest under ``## Notes``.

    This prose is the only differentiated, non-templated content the catalog
    has -- 119 hand-written files that the pages previously surfaced as a bare
    filename. Without it the case pages are boilerplate variants, which is what
    a search engine calls thin content.

    The leading H1 is dropped so the page keeps exactly one, and every
    remaining heading is demoted one level so the notes nest correctly.
    """
    path = case_dir / notes_name
    if not path.exists():
        return []

    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    out: list[str] = []
    in_fence = False
    seen_h1 = False
    for line in raw.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue

        match = re.match(r"^(#{1,6})(\s+)(.*)$", line)
        if match is None:
            out.append(line)
            continue

        hashes, gap, text = match.groups()
        # The notes' own title duplicates the page's H1 (the case title), so it
        # is dropped rather than demoted.
        if len(hashes) == 1 and not seen_h1:
            seen_h1 = True
            continue
        level = min(len(hashes) + _NOTES_HEADING_SHIFT, _MAX_HEADING_LEVEL)
        out.append(f"{'#' * level}{gap}{text}")

    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()
    if not out:
        return []

    return ["## Notes", "", *out, ""]


def _install_cta() -> list[str]:
    """Return the consistent conversion path from a catalog page to PyPI."""
    return [
        "## Use GeoCase in your tests",
        "",
        "Install the complete set of vector, raster, and NetCDF dependencies:",
        "",
        "```bash",
        'pip install "geocase[all]"',
        "```",
        "",
        "[View GeoCase on PyPI](https://pypi.org/project/geocase/).",
        "",
    ]


def _render_case_page(
    case: Any,
    all_cases: list[Any],
    site_url: str,
    hub_risks: set[str],
    case_dir: Path | None = None,
) -> str:
    """Render the full markdown page for a single case."""
    lines = _front_matter(case.title, _meta_description(case))
    lines.extend(_generated_note())
    lines.append(f"# {case.title}")
    lines.append("")

    lines.extend(_badges(case))

    if case.description:
        lines.append(_collapse(case.description))
        lines.append("")

    # The schematic sits above the tables: it answers "what shape of thing is
    # this?" in one glance, which is the question the tables answer slowly.
    # Case pages render at /catalog/cases/<id>/ -- two levels below the
    # catalog root, where the previews directory sits.
    lines.extend(case_diagram(case, GEOMETRY_PROVIDER, _preview_urls("../../")))

    lines.extend(_table(("Property", "Value"), _attribute_rows(case)))
    lines.append("")

    lines.append("## Use this case")
    lines.append("")
    lines.append("```python")
    lines.append("import pytest")
    lines.append("")
    lines.append("")
    lines.append(f'@pytest.mark.geocase_case("{case.id}")')
    lines.append(f"def test_{case.id}(geocase_case) -> None:")
    lines.append("    data = geocase_case.load()")
    lines.append("    assert data is not None")
    lines.append("```")
    lines.append("")
    lines.extend(_install_cta())

    if case.behavioral_goal:
        lines.append("## What this case checks")
        lines.append("")
        lines.append(_collapse(case.behavioral_goal))
        lines.append("")

    if case.risk_types:
        lines.append("## Risk types covered")
        lines.append("")
        for risk in sorted(case.risk_types):
            if risk in hub_risks:
                # Case pages live at ``catalog/cases/<id>.md`` and risk hubs at
                # ``catalog/risk/<slug>.md``, so the hop is one level, not two.
                lines.append(f"- [`{risk}`](../risk/{_slug(risk)}.md)")
            else:
                lines.append(f"- `{risk}`")
        lines.append("")

    assertion_rows = _assertion_rows(case)
    if assertion_rows:
        lines.append("## Expected behavior")
        lines.append("")
        lines.extend(_table(("Assertion", "Expected"), assertion_rows))
        lines.append("")

    # The hand-written prose sits high on the page, right after what the case
    # asserts: it is the part a reader actually reads, and the tables below it
    # are reference material.
    if case_dir is not None and getattr(case.files, "notes", None):
        lines.extend(_notes_body(case_dir, str(case.files.notes)))

    if case.expected_capabilities:
        lines.append("## Required capabilities")
        lines.append("")
        for capability in case.expected_capabilities:
            lines.append(f"- `{capability}`")
        lines.append("")

    lines.append("## Files")
    lines.append("")
    lines.append(f"- Primary: `{case.files.primary}`")
    for sidecar in getattr(case.files, "sidecars", []):
        lines.append(f"- Sidecar: `{sidecar}`")
    if getattr(case.files, "notes", None):
        # Named for completeness only; its body is rendered above under Notes.
        lines.append(f"- Notes: `{_collapse(str(case.files.notes))}`")
    lines.append("")

    source = getattr(case, "source", None)
    if source is not None and (source.name or source.license or source.url):
        lines.append("## Source and license")
        lines.append("")
        if source.name:
            lines.append(f"- Source: {source.name}")
        if source.license:
            lines.append(f"- License: {source.license}")
        if source.url:
            lines.append(f"- URL: <{source.url}>")
        if source.derived_from:
            lines.append(f"- Derived from: {source.derived_from}")
        lines.append("")

    if case.tags:
        lines.append("## Tags")
        lines.append("")
        lines.append(" ".join(f"`{tag}`" for tag in sorted(case.tags)))
        lines.append("")

    related = _related_cases(case, all_cases)
    if related:
        lines.append("## Related cases")
        lines.append("")
        for other in related:
            lines.append(f"- [{other.title}]({other.id}.md) -- `{other.id}`")
        lines.append("")

    lines.extend(_json_ld(case, site_url))
    return "\n".join(lines).rstrip() + "\n"


#: Sort key for the compare table: related shapes should sit adjacent, so
#: category groups first, then geometry type, then id for stability.
def _compare_sort_key(case: Any) -> tuple[str, str, str]:
    return (_value(case.category), _value(case.geometry_type), case.id)


def _html_escape(text: str) -> str:
    return (
        str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ).replace('"', "&quot;")


def _coverage_maps(cases: list[Any]) -> list[str]:
    """Two world maps -- vector and raster -- above the compare table.

    Two rather than one, and that is a requirement rather than a layout
    preference. 23 of the bundled rasters share a single synthetic UTM 33N
    transform and the vector baselines pile onto two more points, so a single
    combined map would put 130 markers on roughly four dots and tell a reader
    nothing. Split by category, each map is legible on its own terms.
    """
    groups = [
        (
            "Vector coverage",
            [case for case in cases if _value(case.category) == "vector"],
            "Where the vector cases sit. Most are synthetic fixtures placed at "
            "shared convenience origins in Central Europe, so co-located cases "
            "are collapsed into one marker carrying a count.",
        ),
        (
            "Raster coverage",
            [case for case in cases if _value(case.category) == "raster"],
            "Where the raster cases sit. The large cluster is the shared "
            "UTM 33N fixture transform; the dashed edges of the map are the "
            "antimeridian, which several cases deliberately straddle.",
        ),
    ]

    lines = ["## Where these cases are", ""]
    lines.append(
        "A case's CRS says what coordinate convention it uses, not where it is. "
        "These maps plot each case at its computed WGS84 extent. Cases with no "
        "valid position -- a deliberately malformed geometry, coordinates "
        "outside the WGS84 domain -- are absent rather than invented."
    )
    lines.append("")

    for title, group, blurb in groups:
        svg = world_map(group, title)
        if not svg:
            continue
        placed = len([case for case in group if getattr(case, "extent", None)])
        lines.append(f"### {title}")
        lines.append("")
        lines.append('<figure class="gc-figure gc-map-figure">')
        lines.append(svg)
        lines.append(
            f"<figcaption>{blurb} {placed} of {len(group)} "
            f"{title.split()[0].lower()} cases have a resolvable extent."
            "</figcaption>"
        )
        lines.append("</figure>")
        lines.append("")

    return lines


def _render_compare_page(cases: list[Any]) -> str:
    """Render the single table that puts every case side by side.

    Raw HTML rather than a Markdown table: the preview cells carry inline SVG,
    and the filter/sort script needs per-row data attributes to work from. The
    table is complete as rendered -- ``docs/javascripts/catalog-compare.js`` is
    progressive enhancement, and the page is fully readable without it.
    """
    ordered = sorted(cases, key=_compare_sort_key)
    # compare.md is served at /catalog/compare/, a directory of its own, so
    # every relative target here is one level below the catalog root. A bare
    # ``cases/<id>/`` would resolve to /catalog/compare/cases/<id>/.
    preview_urls = _preview_urls("../")

    lines = _front_matter(
        "Compare All Cases",
        f"Filter and sort all {len(ordered)} GeoCase test cases in one table, "
        "with a preview of each case's geometry.",
    )
    lines.extend(_generated_note())
    lines.append("# Compare All Cases")
    lines.append("")
    lines.append(
        f"Every one of the {len(ordered)} bundled cases in one table, sorted by "
        "category and geometry type so related shapes sit together. Vector previews "
        "are drawn from each case's real coordinates and raster previews from its "
        "real pixels, with NoData in magenta; a raster that declares no pixel shape "
        "shows a band-structure schematic instead, and NetCDF cases have no drawable "
        "diagram."
    )
    lines.append("")
    lines.extend(_install_cta())
    lines.extend(_coverage_maps(ordered))

    lines.append("## All cases")
    lines.append("")
    lines.append('<div class="gc-compare-controls">')
    lines.append(
        '<input type="search" id="gc-compare-search" class="gc-compare-search" '
        'placeholder="Filter by id, title, or risk type" '
        'aria-label="Filter cases by id, title, or risk type">'
    )
    for field, label in (
        ("category", "Category"),
        ("format", "Format"),
        ("geometry", "Geometry"),
    ):
        values = sorted(
            {
                _row_field(case, field)
                for case in ordered
                if _row_field(case, field) != "--"
            }
        )
        options = "".join(
            f'<option value="{_html_escape(value)}">{_html_escape(value)}</option>'
            for value in values
        )
        lines.append(
            f'<select class="gc-compare-filter" data-field="{field}" '
            f'aria-label="Filter by {label.lower()}">'
            f'<option value="">All {label.lower()}s</option>{options}</select>'
        )
    lines.append(
        f'<span class="gc-compare-count" id="gc-compare-count">'
        f"Showing {len(ordered)} of {len(ordered)} cases</span>"
    )
    lines.append("</div>")
    lines.append("")

    lines.append('<div class="gc-compare-wrap">')
    lines.append('<table class="gc-compare" id="gc-compare-table">')
    lines.append("<thead><tr>")
    lines.append('<th scope="col">Preview</th>')
    for field, label in (
        ("case", "Case"),
        ("category", "Category"),
        ("format", "Format"),
        ("geometry", "Geometry"),
        ("crs", "CRS"),
        ("risk", "Risk types"),
    ):
        lines.append(f'<th scope="col" data-sort="{field}">{label}</th>')
    lines.append("</tr></thead>")
    lines.append("<tbody>")

    for case in ordered:
        risks = sorted(case.risk_types)
        risk_text = ", ".join(risks) if risks else "--"
        crs = case.crs or "--"
        thumb = case_thumbnail(case, GEOMETRY_PROVIDER, preview_urls) or "&mdash;"
        haystack = " ".join([case.id, str(case.title), *risks]).lower()
        lines.append(
            f'<tr data-case-id="{case.id}" '
            f'data-category="{_html_escape(_value(case.category))}" '
            f'data-format="{_html_escape(_value(case.format))}" '
            f'data-geometry="{_html_escape(_row_field(case, "geometry"))}" '
            f'data-search="{_html_escape(haystack)}">'
        )
        lines.append(f'<td class="gc-compare-preview">{thumb}</td>')
        lines.append(
            f'<td><a class="gc-compare-link" href="../cases/{case.id}/">'
            f"{_html_escape(case.title)}</a>"
            f'<br><code class="gc-compare-id">{case.id}</code></td>'
        )
        lines.append(f"<td>{_html_escape(_value(case.category))}</td>")
        lines.append(f"<td>{_html_escape(_value(case.format))}</td>")
        lines.append(f"<td>{_html_escape(_row_field(case, 'geometry'))}</td>")
        lines.append(f"<td><code>{_html_escape(crs)}</code></td>")
        lines.append(f'<td class="gc-compare-risks">{_html_escape(risk_text)}</td>')
        lines.append("</tr>")

    lines.append("</tbody>")
    lines.append("</table>")
    lines.append("</div>")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _row_field(case: Any, field: str) -> str:
    """Return the filterable value of one compare-table column."""
    if field == "category":
        return _value(case.category)
    if field == "format":
        return _value(case.format)
    if field == "geometry":
        return _value(case.geometry_type) or "--"
    raise ValueError(f"unknown compare field: {field}")


def _render_hub_page(
    *,
    title: str,
    description: str,
    intro: str,
    cases: list[Any],
    link_prefix: str,
) -> str:
    """Render a hub page listing every case under one facet value."""
    lines = _front_matter(title, description)
    lines.extend(_generated_note())
    lines.append(f"# {title}")
    lines.append("")
    lines.append(intro)
    lines.append("")
    lines.extend(_install_cta())

    # The grid first, then the table. Someone landing on a risk hub is asking
    # "what kind of data trips this?" -- the schematics answer that before the
    # table's names do.
    # Hub pages render at /catalog/<facet>/<slug>/, so cases sit two levels up.
    lines.extend(
        _case_grid(sorted(cases, key=lambda item: item.id), "../../cases/", "../../")
    )

    lines.append("| Case | Category | Format | Geometry |")
    lines.append("|---|---|---|---|")
    for case in sorted(cases, key=lambda item: item.id):
        geometry = _value(case.geometry_type) or "--"
        lines.append(
            f"| [{case.title}]({link_prefix}{case.id}.md) "
            f"| {_value(case.category)} | {_value(case.format)} | {geometry} |"
        )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_index(
    cases: list[Any],
    by_risk: dict[str, list[Any]],
    by_format: dict[str, list[Any]],
    hub_risks: set[str],
) -> str:
    """Render the catalog landing page."""
    by_category: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        by_category[_value(case.category)].append(case)

    lines = _front_matter(
        "Case Catalog",
        f"Browse all {len(cases)} curated GeoCase test cases by category, format, and risk type.",
    )
    lines.extend(_generated_note())
    lines.append("# Case Catalog")
    lines.append("")
    lines.append(
        f"GeoCase ships {len(cases)} curated geospatial test cases. "
        "Every case is addressable by ID from a plain `pytest` test."
    )
    lines.append("")
    lines.extend(_install_cta())

    lines.append(
        "[Compare all cases side by side](compare.md) in one filterable, sortable table."
    )
    lines.append("")

    lines.append("## Reading the diagrams")
    lines.append("")
    lines.append(
        "Vector case pages render the case's **actual geometry**, projected to fit a "
        "fixed viewport. Raster pages carry a *schematic* of structure instead: the "
        "band stack, pixel grid, and NoData marker, drawn from metadata."
    )
    lines.append("")
    lines.append('!!! warning "What a diagram does and does not tell you"')
    lines.append("")
    lines.append(
        "    **Vector previews are real coordinates, but scale is not comparable.** "
        "Each is fitted to the viewport independently, so a continent-sized polygon and "
        "a metre-sized one can look identical. A handful of cases are deliberately "
        "malformed and cannot be loaded at all; those fall back to a generic shape for "
        "their geometry type and say so in the caption."
    )
    lines.append("")
    lines.append(
        "    **Raster previews are real pixels, but contrast-stretched.** Brightness "
        "is relative to each case's own range, so it carries no absolute value; "
        "NoData is painted magenta, a colour no valid pixel can take. A raster that "
        "declares no pixel shape gets a band-structure schematic instead, which shows "
        "*that* there are pixels and not their values. NetCDF cases have no diagram "
        "at all. Load the case to see the actual data."
    )
    lines.append("")

    lines.append("## Browse by risk type")
    lines.append("")
    lines.append("Start here if you know the failure mode you want to test against.")
    lines.append("")
    lines.append("| Risk type | Cases |")
    lines.append("|---|---:|")
    for risk in sorted(hub_risks):
        lines.append(f"| [`{risk}`](risk/{_slug(risk)}.md) | {len(by_risk[risk])} |")
    lines.append("")
    lines.append(
        f"A further {len(by_risk) - len(hub_risks)} risk types apply to a single case "
        "and are listed against each case below."
    )
    lines.append("")

    lines.append("## Browse by format")
    lines.append("")
    lines.append("| Format | Cases |")
    lines.append("|---|---:|")
    for fmt in sorted(by_format):
        lines.append(f"| [{fmt}](format/{_slug(fmt)}.md) | {len(by_format[fmt])} |")
    lines.append("")

    lines.append("## All cases by category")
    lines.append("")
    for category in sorted(by_category):
        entries = sorted(by_category[category], key=lambda item: item.id)
        lines.append(f"### {category} ({len(entries)})")
        lines.append("")
        lines.append("| Case | Format | Geometry | Risk types |")
        lines.append("|---|---|---|---|")
        for case in entries:
            geometry = _value(case.geometry_type) or "--"
            risks = ", ".join(f"`{risk}`" for risk in sorted(case.risk_types)) or "--"
            lines.append(
                f"| [{case.title}](cases/{case.id}.md) "
                f"| {_value(case.format)} | {geometry} | {risks} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_pages(cases: list[Any], site_url: str) -> dict[str, str]:
    """Build every catalog page as a mapping of relative path to content."""
    by_risk: dict[str, list[Any]] = defaultdict(list)
    by_format: dict[str, list[Any]] = defaultdict(list)
    for case in cases:
        for risk in case.risk_types:
            by_risk[risk].append(case)
        by_format[_value(case.format)].append(case)

    hub_risks = {
        risk for risk, entries in by_risk.items() if len(entries) >= MIN_HUB_CASES
    }

    pages: dict[str, str] = {
        "index.md": _render_index(cases, by_risk, by_format, hub_risks),
        "compare.md": _render_compare_page(cases),
    }

    case_dirs = case_roots_by_id()
    for case in cases:
        pages[f"cases/{case.id}.md"] = _render_case_page(
            case, cases, site_url, hub_risks, case_dirs.get(case.id)
        )

    for risk in sorted(hub_risks):
        entries = by_risk[risk]
        pages[f"risk/{_slug(risk)}.md"] = _render_hub_page(
            title=f"Risk type: {risk}",
            description=(
                f"{len(entries)} GeoCase test cases that exercise the "
                f"{risk.replace('_', ' ')} failure mode."
            ),
            intro=(
                f"These {len(entries)} cases exercise the `{risk}` failure mode. "
                "Run your function against all of them to check how it behaves."
            ),
            cases=entries,
            link_prefix="../cases/",
        )

    for fmt, entries in by_format.items():
        pages[f"format/{_slug(fmt)}.md"] = _render_hub_page(
            title=f"Format: {fmt}",
            description=f"{len(entries)} GeoCase test cases available in {fmt} format.",
            intro=f"These {len(entries)} cases are packaged as {fmt}.",
            cases=entries,
            link_prefix="../cases/",
        )

    return pages


def write_pages(pages: dict[str, str], output_root: Path) -> int:
    """Write pages to disk, removing stale generated files. Returns file count."""
    if output_root.exists():
        for existing in sorted(output_root.rglob("*.md")):
            existing.unlink()

    for relative, content in sorted(pages.items()):
        target = output_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return len(pages)


def check_pages(pages: dict[str, str], output_root: Path) -> list[str]:
    """Return a list of human-readable drift descriptions, empty when in sync."""
    problems: list[str] = []

    for relative, content in sorted(pages.items()):
        target = output_root / relative
        if not target.exists():
            problems.append(f"missing: {relative}")
        elif target.read_text(encoding="utf-8") != content:
            problems.append(f"out of date: {relative}")

    if output_root.exists():
        expected = set(pages)
        for existing in sorted(output_root.rglob("*.md")):
            relative = existing.relative_to(output_root).as_posix()
            if relative not in expected:
                problems.append(f"stale: {relative}")

    return problems


def _vector_fallbacks(cases: list[Any]) -> list[str]:
    """Return the ids of vector cases whose diagram is an archetype, not real data."""
    if GEOMETRY_PROVIDER is None:
        return [case.id for case in cases if _value(case.category) == "vector"]
    return [
        case.id
        for case in cases
        if _value(case.category) == "vector" and GEOMETRY_PROVIDER(case.id) is None
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate catalog documentation pages."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
        help="Directory to write generated catalog pages into.",
    )
    parser.add_argument(
        "--site-url",
        default=DEFAULT_SITE_URL,
        help="Canonical site URL used in JSON-LD.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed pages match the catalog instead of writing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    cases = sorted(get_registry().list_cases(), key=lambda case: case.id)
    if not cases:
        print("No cases found in the registry.")
        return 1

    fallbacks = _vector_fallbacks(cases)
    if len(fallbacks) > MAX_VECTOR_FALLBACKS:
        print(
            f"{len(fallbacks)} of the vector cases could not be loaded, so their "
            "diagrams would fall back to generic archetypes."
        )
        print(
            "This almost always means the geospatial stack is missing. Run from the "
            "conda `geocase` environment, or install `.[raster,vector]`."
        )
        return 1

    pages = build_pages(cases, args.site_url.rstrip("/"))

    if args.check:
        problems = check_pages(pages, args.output_root)
        if problems:
            print(f"Catalog pages are out of date ({len(problems)} problem(s)):")
            for problem in problems:
                print(f"  - {problem}")
            print("\nRegenerate with: python scripts/generate_catalog_pages.py")
            return 1
        print(f"Catalog pages are up to date ({len(pages)} files, {len(cases)} cases).")
        return 0

    written = write_pages(pages, args.output_root)
    print(f"Wrote {written} catalog pages for {len(cases)} cases to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
