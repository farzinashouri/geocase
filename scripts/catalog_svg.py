"""Inline SVG schematics for the generated catalog pages.

This module itself stays *dependency-free*: on its own it draws from metadata
only -- geometry type, raster shape, band count, dtype, nodata convention --
so it is importable and testable from a plain checkout with no geospatial
stack, and the committed output stays text so ``--check`` diffs are readable.

A caller that *does* have the stack can pass a ``geometry_provider``: a
callable taking a case id and returning that case's loaded GeoDataFrame (or
``None``). Vector diagrams then show the case's real coordinates instead of an
archetype of its geometry type. ``generate_catalog_pages.py`` supplies one; the
projection itself lives in :mod:`catalog_geometry`.

A caller can likewise pass a ``preview_url_provider``: a callable taking a
case id and returning the URL of that case's stored pixel preview (generated
by ``generate_raster_previews.py``), or ``None``. Raster cases then show their
real pixels instead of the band-stack schematic. NetCDF stays undrawable.

The real and metadata paths are captioned differently, and that distinction is
not cosmetic: a page that claims to show real data while drawing an archetype
is lying about its own provenance.

Colours are CSS custom properties defined in ``docs/stylesheets/catalog.css``
so the diagrams follow the Material light/dark toggle. Nothing here hard-codes
a hex value that would strand a diagram in one scheme.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


# Viewport for every schematic. Fixed so pages align in the index grid; the
# shapes below are laid out in these coordinates directly.
WIDTH = 120
HEIGHT = 80

_STROKE = 'stroke="var(--gc-diagram-stroke)"'
_FILL = 'fill="var(--gc-diagram-fill)"'
_ACCENT = 'fill="var(--gc-diagram-accent)"'
_MUTED = 'fill="var(--gc-diagram-muted)"'


def _open(label: str) -> list[str]:
    """Open an SVG with an accessible label.

    The diagram is decorative-but-informative: it repeats structure stated in
    the tables below it, so it gets a role and a title rather than being hidden.
    """
    return [
        f'<svg class="gc-diagram" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'role="img" aria-label="{label}" xmlns="http://www.w3.org/2000/svg">',
        f"<title>{label}</title>",
    ]


def _frame() -> str:
    """A neutral bounding frame, so every schematic shares one visual anchor."""
    return (
        f'<rect x="1" y="1" width="{WIDTH - 2}" height="{HEIGHT - 2}" rx="3" '
        f'fill="none" {_STROKE} stroke-width="1" opacity="0.35"/>'
    )


# --- vector schematics -------------------------------------------------------
#
# One drawing per geometry type. The coordinates are illustrative archetypes,
# chosen to make the *type* unmistakable at thumbnail size -- a Polygon must
# not be confusable with a MultiPolygon at 120x80.


def _points(coords: list[tuple[int, int]]) -> str:
    return "".join(f'<circle cx="{x}" cy="{y}" r="4" {_ACCENT}/>' for x, y in coords)


def _polyline(coords: list[tuple[int, int]], closed: bool = False) -> str:
    pts = " ".join(f"{x},{y}" for x, y in coords)
    tag = "polygon" if closed else "polyline"
    fill = _FILL if closed else 'fill="none"'
    return f'<{tag} points="{pts}" {fill} {_STROKE} stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'


_VECTOR_SHAPES: dict[str, list[str]] = {
    "Point": [_points([(60, 40)])],
    "MultiPoint": [_points([(34, 30), (62, 52), (86, 26)])],
    "LineString": [_polyline([(20, 58), (46, 30), (72, 50), (98, 22)])],
    "MultiLineString": [
        _polyline([(20, 60), (44, 40), (66, 54)]),
        _polyline([(56, 26), (80, 40), (100, 22)]),
    ],
    "Polygon": [_polyline([(28, 22), (92, 30), (84, 62), (34, 58)], closed=True)],
    "MultiPolygon": [
        _polyline([(18, 26), (54, 22), (50, 54), (22, 52)], closed=True),
        _polyline([(66, 34), (100, 30), (98, 60), (70, 62)], closed=True),
    ],
    "GeometryCollection": [
        _polyline([(16, 30), (46, 26), (44, 54), (20, 56)], closed=True),
        _polyline([(58, 58), (76, 34), (96, 48)]),
        _points([(92, 22)]),
    ],
}


def _vector_svg(geometry_type: str) -> str | None:
    shapes = _VECTOR_SHAPES.get(geometry_type)
    if not shapes:
        return None
    label = f"Schematic of a {geometry_type} geometry"
    lines = _open(label)
    lines.append(_frame())
    lines.extend(shapes)
    lines.append("</svg>")
    return "".join(lines)


# --- real geometry previews --------------------------------------------------
#
# Presentation for the projected geometry. These mirror the archetype styling
# above so a preview and a fallback sit together in one grid without one
# looking like a different kind of object.

_POINT_ATTRS = f'r="3" {_ACCENT}'
_LINE_ATTRS = (
    f'fill="none" {_STROKE} stroke-width="2" '
    'stroke-linejoin="round" stroke-linecap="round"'
)
_AREA_ATTRS = (
    f'{_FILL} fill-rule="evenodd" {_STROKE} stroke-width="1.5" stroke-linejoin="round"'
)

#: A vector case id maps to its loaded GeoDataFrame, or ``None`` when the case
#: cannot be loaded (``unclosed_ring_polygon`` is deliberately malformed).
GeometryProvider = Callable[[str], Any]


# Re-exported from :mod:`catalog_geometry`, which owns the coordinates and so
# owns the thinning. It lives there, not here, because this module imports that
# one lazily -- the reverse edge would be a cycle -- but the thumbnail point
# budget is a rendering concern, so it is reachable under this name too.
try:
    from catalog_geometry import (  # noqa: F401
        _MAX_THUMBNAIL_POINTS,
        _decimate,
    )
except ImportError:  # pragma: no cover - only when scripts/ is off sys.path
    pass


def _preview_svg(case: Any, provider: GeometryProvider) -> str | None:
    """Draw the case's real geometry, or ``None`` to fall back to the archetype."""
    try:
        from catalog_geometry import geometry_shapes
    except ImportError:
        return None

    try:
        gdf = provider(case.id)
        shapes = geometry_shapes(
            gdf,
            WIDTH,
            HEIGHT,
            point_attrs=_POINT_ATTRS,
            line_attrs=_LINE_ATTRS,
            area_attrs=_AREA_ATTRS,
        )
    except Exception:
        # Broken fixtures are part of the catalog's point, so a load or
        # projection failure is an expected outcome here, not an error.
        return None
    if not shapes:
        return None

    geom = str(getattr(case.geometry_type, "value", case.geometry_type))
    lines = _open(f"{geom} geometry of {case.id}, rendered from the case's data")
    lines.append(_frame())
    lines.extend(shapes)
    lines.append("</svg>")
    return "".join(lines)


def _vector_render(
    case: Any, provider: GeometryProvider | None
) -> tuple[str | None, bool]:
    """Return ``(svg, is_real)`` for a vector case, preferring the real geometry."""
    if provider is not None:
        svg = _preview_svg(case, provider)
        if svg is not None:
            return svg, True

    geom = getattr(case.geometry_type, "value", case.geometry_type)
    if not geom:
        return None, False
    return _vector_svg(str(geom)), False


# --- raster schematics -------------------------------------------------------


#: A raster case id maps to the URL of its stored pixel preview, or ``None``
#: when that case has no preview (no declared shape, or an unreadable payload).
#: The URL is relative to the page being rendered, so the provider the
#: generator supplies is page-specific -- see ``generate_catalog_pages.py``.
PreviewUrlProvider = Callable[[str], str | None]


def _raster_preview(case: Any, provider: PreviewUrlProvider) -> str | None:
    """Reference the case's stored pixel preview, or ``None`` to fall back.

    An ``<img>`` rather than an inlined data-URI: the previews are files
    precisely so the ``--check`` diff names the case whose pixels moved, and
    inlining them here would put the base64 back into the markdown it was
    kept out of.
    """
    # ``expected_shape`` is the same selector ``catalog_raster.preview_cases``
    # uses. Checking it here too means a provider that answers for every id
    # cannot put an ``<img>`` on a page whose case has no preview file.
    shape = getattr(getattr(case, "assertions", None), "expected_shape", None)
    if not shape:
        return None

    try:
        url = provider(case.id)
    except Exception:
        return None
    if not url:
        return None

    dims = "x".join(str(dim) for dim in shape)
    label = f"Pixels of {case.id}, a {dims} raster, with NoData in magenta"
    return (
        f'<img class="gc-diagram gc-preview" src="{url}" alt="{label}" '
        'loading="lazy" decoding="async">'
    )


def _raster_svg(case: Any) -> str | None:
    """Draw a band stack, with grid density hinting at the pixel shape.

    Bands are drawn as offset planes because band count is the property most
    often got wrong by a loader (see the ``band_loss`` and
    ``incorrect_band_order`` risk types), so it deserves the most visual weight.
    """
    assertions = getattr(case, "assertions", None)
    if assertions is None:
        return None

    bands = assertions.expected_band_count
    shape = assertions.expected_shape
    if not bands and not shape:
        return None

    band_count = bands or 1
    # Beyond four planes the stack stops being readable; the caption carries
    # the true number, so cap the drawing rather than shrinking it.
    drawn = min(band_count, 4)

    label_bits = []
    if bands:
        label_bits.append(f"{bands} band{'s' if bands != 1 else ''}")
    if shape:
        label_bits.append("x".join(str(dim) for dim in shape))
    label = "Schematic raster: " + ", ".join(label_bits)

    lines = _open(label)
    lines.append(_frame())

    step = 6
    plane_w, plane_h = 58, 34
    # Centre the whole stack in the viewport, so a 4-plane diagram sits in the
    # frame exactly as a 1-plane one does rather than growing out of it.
    span = (drawn - 1) * step
    x0 = (WIDTH - plane_w - span) / 2
    y0 = (HEIGHT - plane_h - span) / 2
    # Back-to-front so nearer planes overlap the ones behind them.
    for index in range(drawn - 1, -1, -1):
        x = x0 + index * step
        y = y0 + (drawn - 1 - index) * step
        front = index == 0
        fill = _FILL if front else _MUTED
        lines.append(
            f'<rect x="{x}" y="{y}" width="{plane_w}" height="{plane_h}" rx="2" '
            f'{fill} {_STROKE} stroke-width="1.5"/>'
        )
        if front:
            front_x, front_y = x, y
            # A light grid on the front plane only: it reads as "pixels" without
            # implying the real resolution, which is in the caption.
            for col in range(1, 4):
                gx = x + col * plane_w / 4
                lines.append(
                    f'<line x1="{gx:.1f}" y1="{y}" x2="{gx:.1f}" y2="{y + plane_h}" '
                    f'{_STROKE} stroke-width="0.5" opacity="0.4"/>'
                )
            for row in range(1, 3):
                gy = y + row * plane_h / 3
                lines.append(
                    f'<line x1="{x}" y1="{gy:.1f}" x2="{x + plane_w}" y2="{gy:.1f}" '
                    f'{_STROKE} stroke-width="0.5" opacity="0.4"/>'
                )

    if assertions.nodata_convention and assertions.nodata_convention != "none":
        # One dashed cell marks "this case carries NoData", the single most
        # common raster trap in the catalog. It snaps to the front plane's
        # top-left grid cell so it never collides with the planes behind it.
        cell_w = plane_w / 4
        cell_h = plane_h / 3
        # The bottom-left cell specifically: the stack recedes up and to the
        # right, so that corner is the one no other plane overlaps.
        lines.append(
            f'<rect x="{front_x + 1:.1f}" y="{front_y + plane_h - cell_h + 1:.1f}" '
            f'width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" '
            f'fill="none" {_STROKE} stroke-width="1.2" stroke-dasharray="2 1.5"/>'
        )

    lines.append("</svg>")
    return "".join(lines)


def _caption(case: Any, is_real: bool = False) -> str:
    """One line naming what the diagram is asserting, so it is falsifiable.

    ``is_real`` distinguishes the real-data path from the metadata one, for
    both vector and raster. It must track what was actually drawn: the caption
    is the only thing on the page telling a reader whether they are looking at
    this case's own bytes or at a drawing of its metadata.
    """
    category = str(getattr(case.category, "value", case.category))
    assertions = getattr(case, "assertions", None)

    if category == "vector":
        geom = str(getattr(case.geometry_type, "value", case.geometry_type))
        if is_real:
            # Deliberately silent about scale: the fit-to-viewport transform
            # normalizes it away, so a continent and a car park can look alike.
            return (
                f"{geom} geometry, rendered from the case's actual geometry. "
                "Scale is normalized to the viewport and is not comparable between cases."
            )
        return (
            f"Schematic only -- this case's geometry could not be rendered, so the "
            f"drawing is a generic {geom}, not the fixture's coordinates."
        )

    bits = []
    if assertions is not None:
        if assertions.expected_band_count:
            count = assertions.expected_band_count
            bits.append(f"{count} band{'s' if count != 1 else ''}")
        if assertions.expected_shape:
            bits.append("x".join(str(dim) for dim in assertions.expected_shape) + " px")
        if assertions.expected_dtype:
            bits.append(str(assertions.expected_dtype))
        if assertions.nodata_convention and assertions.nodata_convention != "none":
            bits.append(f"{assertions.nodata_convention} NoData")
    detail = ", ".join(bits)
    if is_real:
        # Same honesty constraint as the vector preview caption: the pixels are
        # this case's own, but the display is contrast-stretched to 0-255, so
        # brightness carries no absolute meaning.
        return (
            f"{detail}. Rendered from the case's actual pixels, contrast-stretched "
            "for display; NoData is shown in magenta."
        )
    return f"Schematic: {detail}. Drawn from metadata, not from the pixels."


def _render(
    case: Any,
    provider: GeometryProvider | None,
    preview_url_provider: PreviewUrlProvider | None = None,
) -> tuple[str | None, bool]:
    category = str(getattr(case.category, "value", case.category))
    if category == "vector":
        return _vector_render(case, provider)
    if category == "raster":
        if preview_url_provider is not None:
            preview = _raster_preview(case, preview_url_provider)
            if preview is not None:
                return preview, True
        return _raster_svg(case), False
    return None, False


def case_diagram(
    case: Any,
    geometry_provider: GeometryProvider | None = None,
    preview_url_provider: PreviewUrlProvider | None = None,
) -> list[str]:
    """Return the markdown lines for a case's diagram, or [] if undrawable.

    Callers append this straight into the page body. Returning an empty list
    for the undrawable cases (netcdf, and rasters with no declared shape or
    band count) is intentional -- a placeholder box would assert structure the
    metadata does not actually have.

    Pass ``geometry_provider`` to draw vector cases from their real geometry
    and ``preview_url_provider`` to show raster cases' real pixels; without
    either, every diagram is metadata-only.
    """
    svg, is_real = _render(case, geometry_provider, preview_url_provider)
    if svg is None:
        return []

    return [
        '<figure class="gc-figure">',
        svg,
        f"<figcaption>{_caption(case, is_real)}</figcaption>",
        "</figure>",
        "",
    ]


def case_thumbnail(
    case: Any,
    geometry_provider: GeometryProvider | None = None,
    preview_url_provider: PreviewUrlProvider | None = None,
) -> str:
    """Return a bare inline SVG or preview ``<img>``, or "" if undrawable."""
    svg, _ = _render(case, geometry_provider, preview_url_provider)
    return svg or ""


# --- world maps --------------------------------------------------------------
#
# Where the catalog's data actually sits on Earth. A locator map, not a
# basemap: no tiles, no CDN, no JavaScript, because the docs build ships none
# of those and the ``--check`` text-diff gate is worth more than pan-and-zoom.
#
# Equirectangular (plate carree) throughout. It is the projection whose
# lon/lat -> pixel transform is a bare scale, which keeps the antimeridian
# handling below legible; the price is Antarctica and Greenland looking
# enormous, which for placing a marker does not matter.

#: A coarse continental outline, as flat "lon,lat,lon,lat,..." strings in
#: WGS84 degrees. 11 rings, ~460 points, derived once from Natural Earth 110m
#: (public domain) simplified to ~1.2 degrees and pasted here as data.
#:
#: Embedded rather than loaded because this module's defining constraint is
#: that it is *dependency-free* -- importable and testable from a plain
#: checkout, with the docs build fetching nothing. At the ~720px width these
#: maps render, finer than a degree is invisible anyway, so the coarseness
#: costs nothing a reader would notice.
_COASTLINE = [
    "-9.0,4.8,-16.6,12.2,-17.1,21.0,-5.9,35.8,9.5,37.3,11.1,36.9,10.3,33.8,19.1,30.3,21.5,32.8,33.8,31.0,36.2,36.7,27.6,36.7,26.2,39.5,33.5,42.0,41.6,41.5,36.7,45.2,39.1,47.3,33.9,44.4,30.7,46.6,27.7,42.6,28.8,41.1,22.6,40.3,24.0,37.7,22.5,36.4,19.5,41.7,13.1,45.7,12.6,44.1,18.5,40.2,16.9,40.4,16.1,38.0,8.9,44.4,3.1,43.1,-2.1,36.7,-8.9,36.9,-9.4,43.0,-1.4,44.0,-1.2,46.0,-4.6,48.7,8.1,53.5,8.5,57.1,10.6,57.7,10.9,54.0,19.7,54.4,21.6,57.4,24.1,57.0,23.3,59.2,29.1,60.0,21.3,60.7,21.5,63.2,25.4,65.1,23.9,66.0,17.8,62.7,18.8,60.1,15.9,56.1,12.9,55.4,10.4,59.5,5.7,58.6,5.0,62.0,19.2,69.8,28.2,71.2,41.1,67.5,33.2,66.6,37.0,63.8,43.9,66.1,43.5,68.6,46.3,68.2,46.3,66.7,53.7,68.9,59.9,68.3,60.6,69.9,68.5,68.1,66.7,71.0,69.9,73.0,72.8,72.2,72.4,66.2,75.1,67.8,73.1,71.4,74.7,72.8,76.4,71.2,81.5,71.8,80.5,73.6,104.4,77.7,114.1,75.8,109.4,74.2,127.0,73.6,131.3,70.8,140.5,72.8,160.9,69.4,180.0,69.0,180.0,65.0,177.4,64.6,179.2,62.3,163.5,59.9,162.1,54.9,156.8,51.0,155.9,56.8,164.5,62.6,160.1,60.5,156.7,61.4,155.0,59.1,142.2,59.0,135.1,54.7,139.9,54.2,141.4,52.2,138.2,46.3,127.5,39.8,129.1,35.1,126.5,34.4,125.3,39.6,121.1,38.9,121.6,40.9,118.0,39.2,118.9,37.4,122.4,37.5,119.2,34.9,121.9,31.7,121.7,28.2,115.9,22.8,105.9,19.8,109.3,13.4,105.2,8.6,100.1,13.4,99.2,9.2,104.2,1.3,98.3,7.8,97.2,16.9,94.2,16.0,91.4,22.8,87.0,21.5,80.3,15.9,79.9,10.4,77.5,8.0,72.6,21.4,70.5,20.9,66.4,25.4,57.4,25.7,56.5,27.1,51.5,27.9,50.1,30.1,48.0,30.0,51.8,24.0,56.4,26.4,59.8,22.3,55.3,17.2,43.5,12.6,34.8,29.8,33.9,27.6,32.4,29.9,42.7,11.7,44.6,10.4,51.1,12.0,51.0,10.6,47.7,4.2,39.2,-4.7,40.1,-16.1,34.8,-19.8,35.5,-24.1,25.8,-33.9,18.4,-34.1,15.2,-27.1,11.6,-16.7,13.2,-8.6,8.8,-1.1,9.8,3.1,8.5,4.8,5.9,4.3,4.3,6.3,-9.0,4.8",
    "-78.2,8.3,-80.9,7.2,-85.7,9.9,-87.5,13.3,-103.5,18.3,-114.8,31.8,-109.4,23.2,-112.2,24.7,-124.4,40.3,-124.7,48.2,-122.6,47.1,-122.8,49.0,-125.6,50.4,-127.4,50.8,-134.1,58.1,-147.1,60.9,-151.7,59.2,-150.6,61.3,-158.4,56.0,-164.8,54.4,-157.0,58.9,-165.3,60.5,-165.7,62.1,-160.8,64.8,-168.1,65.7,-161.7,66.1,-166.8,68.4,-156.6,71.4,-96.1,67.3,-94.2,69.1,-96.4,71.2,-93.9,71.8,-87.4,67.2,-85.5,69.9,-81.2,68.7,-81.4,67.1,-85.8,66.6,-94.2,60.9,-94.7,58.9,-92.3,57.1,-82.3,55.1,-79.9,51.2,-78.6,52.6,-79.8,54.7,-76.5,56.5,-78.5,58.8,-78.1,62.3,-73.8,62.4,-69.6,61.1,-67.6,58.2,-64.6,60.3,-61.8,56.3,-55.8,53.3,-60.0,50.2,-66.4,50.2,-71.1,46.8,-65.1,49.2,-64.5,46.2,-63.2,45.7,-61.5,45.9,-60.5,47.0,-59.8,45.9,-65.4,43.5,-64.4,45.3,-67.1,45.1,-70.6,43.1,-70.0,41.6,-75.5,39.5,-75.1,38.4,-75.9,37.2,-76.4,39.1,-75.7,35.6,-81.3,31.4,-80.4,25.2,-83.7,29.9,-86.4,30.4,-93.8,29.7,-97.4,27.4,-97.9,22.4,-95.9,18.8,-91.4,18.9,-90.3,21.0,-87.1,21.5,-88.9,15.9,-83.4,15.3,-82.2,9.0,-76.8,8.6,-71.8,12.4,-71.7,9.1,-69.9,12.2,-68.2,10.6,-61.9,10.7,-62.4,9.9,-57.1,6.0,-51.3,4.2,-50.7,0.2,-48.6,-1.2,-35.2,-5.5,-35.1,-9.0,-38.7,-13.1,-40.9,-21.9,-47.6,-24.9,-53.8,-34.4,-58.4,-33.9,-56.8,-36.9,-65.1,-41.1,-63.5,-42.6,-67.3,-45.6,-66.0,-48.1,-69.1,-50.7,-68.1,-52.3,-69.5,-52.3,-70.8,-52.9,-71.0,-53.8,-74.9,-52.3,-75.6,-48.7,-74.1,-46.9,-75.6,-46.6,-72.7,-42.4,-74.3,-43.2,-70.2,-19.8,-76.0,-14.6,-81.2,-6.1,-79.8,-2.7,-80.9,-1.1,-77.1,3.8,-78.2,8.3",
    "-180.0,-84.7,-143.1,-85.0,-153.6,-83.7,-152.9,-82.0,-156.8,-81.1,-146.4,-80.3,-155.3,-79.1,-158.4,-76.9,-151.3,-77.4,-144.9,-75.2,-119.7,-74.5,-113.9,-73.7,-100.1,-74.9,-103.7,-72.6,-68.9,-73.0,-67.1,-72.0,-68.5,-69.7,-67.3,-66.9,-63.0,-64.6,-57.8,-63.3,-65.7,-68.0,-60.8,-73.7,-77.2,-76.7,-73.7,-77.9,-78.0,-79.2,-58.2,-83.2,-28.5,-80.3,-35.8,-78.3,-17.5,-75.1,-6.9,-70.9,27.1,-70.5,33.9,-68.5,38.6,-69.8,54.5,-65.8,68.9,-67.9,67.9,-71.9,69.9,-72.3,88.0,-66.2,119.8,-67.3,135.1,-65.3,137.5,-67.0,171.2,-71.7,163.6,-76.2,167.0,-78.8,159.8,-80.9,180.0,-84.7,180.0,-90.0,-180.0,-90.0,-180.0,-84.7",
    "-20.8,82.7,-31.9,82.2,-12.2,81.3,-20.0,80.2,-17.7,80.1,-19.7,78.8,-18.5,77.0,-21.7,76.6,-19.4,74.3,-24.8,72.3,-21.8,70.7,-26.4,70.2,-22.3,70.1,-39.8,65.5,-43.4,60.1,-48.3,60.9,-51.6,63.6,-54.0,67.2,-50.9,69.9,-54.7,69.6,-51.4,70.6,-55.8,71.7,-54.7,72.6,-58.6,75.5,-73.3,78.0,-60.3,82.0,-20.8,82.7",
    "131.3,-31.5,115.0,-34.2,113.7,-22.5,120.9,-19.7,125.7,-14.2,129.6,-15.0,132.4,-11.1,136.5,-11.9,135.5,-15.0,140.2,-17.7,142.5,-10.7,153.6,-28.1,150.0,-37.4,146.3,-39.0,140.6,-38.0,138.2,-34.4,136.8,-35.3,137.8,-32.9,136.0,-34.9,131.3,-31.5",
    "-80.7,72.1,-67.0,69.2,-68.8,68.7,-61.9,66.9,-63.9,65.0,-68.0,66.3,-64.7,63.4,-68.8,63.7,-66.2,61.9,-78.6,64.6,-74.0,65.5,-73.3,68.1,-79.0,70.2,-88.7,70.4,-90.2,72.2,-82.3,73.8,-80.7,72.1",
    "144.6,-3.9,150.7,-10.6,144.7,-7.6,142.6,-9.3,137.6,-8.4,137.9,-5.4,133.0,-4.1,132.0,-2.8,133.7,-2.2,130.5,-0.9,134.0,-0.8,135.5,-3.4,138.3,-1.7,144.6,-3.9",
    "-91.6,81.9,-72.8,83.2,-61.9,82.6,-76.9,79.3,-75.4,78.5,-80.6,76.2,-89.5,76.5,-85.0,77.5,-88.0,78.4,-85.1,79.3,-86.9,80.3,-81.8,80.5,-91.6,81.9",
    "-101.0,70.0,-113.3,68.5,-117.3,70.0,-112.4,70.4,-119.4,71.6,-115.2,73.3,-108.2,71.7,-107.5,73.2,-101.0,70.0",
    "140.3,35.1,135.1,34.6,131.0,33.9,130.7,31.0,129.4,33.3,132.6,35.4,135.7,35.5,141.4,41.4,140.3,35.1",
    "119.0,0.9,114.9,-4.1,110.2,-2.9,109.0,0.4,117.1,6.9,119.2,5.4,117.3,3.2,119.0,0.9",
]

#: Viewport for a world map. 2:1 is the natural aspect of an equirectangular
#: world -- 360 degrees of longitude by 180 of latitude.
MAP_WIDTH = 720
MAP_HEIGHT = 360

#: Graticule spacing in degrees.
_GRATICULE_STEP = 30

#: Two markers closer together than this many pixels collapse into one.
#: Not cosmetic: 23 of the bundled rasters share a single synthetic UTM 33N
#: transform and the vector baselines cluster on two more points, so without
#: clustering a "map" of the raster corpus is one dot wearing 23 hats and the
#: reader learns nothing about how many cases are there.
_CLUSTER_RADIUS = 9.0

#: An extent narrower than this in either axis is drawn as a marker rather
#: than a rectangle -- below it the rectangle is smaller than its own stroke.
_MIN_EXTENT_PIXELS = 4.0

#: A box reaching within this many degrees of a pole, and spanning at least
#: ``_POLE_CAP_MIN_SPAN`` degrees of longitude, is a pole cap: a polygon
#: encircling the pole, whose bounding box legitimately spans half the world.
_POLE_CAP_LATITUDE = 5.0
_POLE_CAP_MIN_SPAN = 120.0

_MAP_LAND = 'fill="var(--gc-map-land)"'
_MAP_GRID = 'stroke="var(--gc-map-grid)"'
_MAP_EDGE = 'stroke="var(--gc-map-edge)"'
_MAP_MARKER = 'fill="var(--gc-map-marker)"'
_MAP_EXTENT = 'fill="var(--gc-map-extent)" stroke="var(--gc-map-marker)"'
_MAP_LABEL = 'fill="var(--gc-map-label)"'


def _map_x(lon: float) -> float:
    return (float(lon) + 180.0) * MAP_WIDTH / 360.0


def _map_y(lat: float) -> float:
    # SVG y grows downward; latitude grows upward.
    return (90.0 - float(lat)) * MAP_HEIGHT / 180.0


def _n(value: float) -> str:
    """Format a viewport coordinate. One decimal is finer than a screen pixel."""
    text = f"{value:.1f}"
    return text[:-2] if text.endswith(".0") else text


def _land() -> list[str]:
    shapes = []
    for ring in _COASTLINE:
        values = [float(v) for v in ring.split(",")]
        points = " ".join(
            f"{_n(_map_x(values[i]))},{_n(_map_y(values[i + 1]))}"
            for i in range(0, len(values), 2)
        )
        shapes.append(f'<polygon points="{points}" {_MAP_LAND}/>')
    return shapes


def _graticule() -> list[str]:
    lines = []
    for lon in range(-180 + _GRATICULE_STEP, 180, _GRATICULE_STEP):
        x = _n(_map_x(lon))
        lines.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{MAP_HEIGHT}" '
            f'{_MAP_GRID} stroke-width="0.5" opacity="0.5"/>'
        )
    for lat in range(-90 + _GRATICULE_STEP, 90, _GRATICULE_STEP):
        y = _n(_map_y(lat))
        lines.append(
            f'<line x1="0" y1="{y}" x2="{MAP_WIDTH}" y2="{y}" '
            f'{_MAP_GRID} stroke-width="0.5" opacity="0.5"/>'
        )
    # The antimeridian gets its own emphasis. The catalog has six cases whose
    # entire subject is this line, so a reader needs to see where it is.
    lines.append(
        f'<line x1="0.5" y1="0" x2="0.5" y2="{MAP_HEIGHT}" '
        f'{_MAP_EDGE} stroke-width="1.5" stroke-dasharray="4 3"/>'
    )
    lines.append(
        f'<line x1="{MAP_WIDTH - 0.5}" y1="0" x2="{MAP_WIDTH - 0.5}" '
        f'y2="{MAP_HEIGHT}" {_MAP_EDGE} stroke-width="1.5" stroke-dasharray="4 3"/>'
    )
    return lines


def _extent_boxes(extent: Any) -> list[tuple[float, float, float, float]]:
    """Return the pixel rectangles for *extent* -- two when it wraps.

    A wrapping box drawn as one rectangle from its west to its east edge is
    exactly the world-spanning lie the wrap convention exists to prevent, so
    it is split at the antimeridian and drawn against both edges instead.
    """
    top = _map_y(extent.north)
    bottom = _map_y(extent.south)
    height = max(bottom - top, 0.0)

    if extent.west > extent.east:
        left = _map_x(extent.west)
        right = _map_x(extent.east)
        return [
            (left, top, MAP_WIDTH - left, height),
            (0.0, top, right, height),
        ]
    left = _map_x(extent.west)
    return [(left, top, _map_x(extent.east) - left, height)]


def _is_pole_cap(extent: Any) -> bool:
    """True when *extent* is the bounding box of a polygon encircling a pole.

    Derived from the extent rather than declared in ``case.yaml``: the case
    schema is gated by strict set equality against ``CaseMetadata.model_fields``,
    so a new field is a schema change -- and more importantly a derived rule
    cannot drift out of agreement with the extent it describes, which a
    hand-maintained ``pole_cap:`` flag eventually would.
    """
    north = float(extent.north)
    south = float(extent.south)
    reaches_pole = (
        north >= 90.0 - _POLE_CAP_LATITUDE or south <= -90.0 + _POLE_CAP_LATITUDE
    )
    if not reaches_pole:
        return False

    west, east = float(extent.west), float(extent.east)
    span = (360.0 - west + east) if west > east else (east - west)
    return span >= _POLE_CAP_MIN_SPAN


def _extent_title(case: Any, is_cap: bool) -> str:
    """The tooltip naming a footprint, so a reader can identify what they see."""
    title = f"{case.id} -- {case.title}"
    region = getattr(case, "region", None)
    if region:
        title += f" ({region})"
    if is_cap:
        title += (
            ". The band is this case's bounding box: the polygon encircles the "
            "pole, so its box spans half the world. It is not the data's shape."
        )
    return title


def _extent_centroid(extent: Any) -> tuple[float, float]:
    """The marker position: the middle of the box, the short way round."""
    if extent.west > extent.east:
        span = (180.0 - extent.west) + (extent.east + 180.0)
        lon = extent.west + span / 2.0
        if lon > 180.0:
            lon -= 360.0
    else:
        lon = (extent.west + extent.east) / 2.0
    return _map_x(lon), _map_y((extent.south + extent.north) / 2.0)


def _cluster(points: list[tuple[float, float, Any]]) -> list[dict[str, Any]]:
    """Greedily merge points within ``_CLUSTER_RADIUS`` into counted clusters.

    Greedy and order-dependent by design: the caller feeds cases in a stable
    sorted order, so the same corpus always produces the same clusters and the
    ``--check`` gate stays a signal rather than a coin flip.
    """
    clusters: list[dict[str, Any]] = []
    for x, y, case in points:
        for cluster in clusters:
            dx = cluster["x"] - x
            dy = cluster["y"] - y
            if dx * dx + dy * dy <= _CLUSTER_RADIUS * _CLUSTER_RADIUS:
                cluster["cases"].append(case)
                break
        else:
            clusters.append({"x": x, "y": y, "cases": [case]})
    return clusters


#: Ids named in full before a cluster label switches to a count. Matches
#: ``MAX_LISTED_IDS`` in ``docs/javascripts/catalog-compare.js``, so the
#: no-JS ``<title>`` fallback and the HTML tooltip say the same thing.
_MAX_LABELLED_IDS = 8


def _cluster_label(cases: list[Any]) -> str:
    """A tooltip naming what sits here, capped so a 36-case cluster stays sane."""
    ids = [str(case.id) for case in cases]
    shown = ", ".join(ids[:_MAX_LABELLED_IDS])
    if len(ids) > _MAX_LABELLED_IDS:
        shown += f", and {len(ids) - _MAX_LABELLED_IDS} more"
    region = next(
        (str(case.region) for case in cases if getattr(case, "region", None)), ""
    )
    head = f"{len(ids)} case{'s' if len(ids) != 1 else ''}"
    if region:
        head += f" -- {region}"
    return f"{head}: {shown}"


def world_map(cases: list[Any], title: str) -> str:
    """Render an equirectangular locator map of *cases*, or "" if none place.

    Each case is plotted at its ``extent``. An extent large enough to be
    visible is also outlined as a rectangle, so a reader can tell a continent-
    sized case from a 16x16 fixture; everything else is a marker. Co-located
    cases collapse into one marker carrying a count -- see
    :data:`_CLUSTER_RADIUS` for why that is required rather than nice.

    Cases with no extent are simply absent. That is honest: four bundled cases
    have no valid WGS84 position, and inventing one for the map would be the
    same defect the extent field was added to remove.
    """
    placed = sorted(
        (case for case in cases if getattr(case, "extent", None) is not None),
        key=lambda case: str(case.id),
    )
    if not placed:
        return ""

    lines = [
        f'<svg class="gc-worldmap" viewBox="0 0 {MAP_WIDTH} {MAP_HEIGHT}" '
        f'role="img" aria-label="{title}: world map of {len(placed)} case '
        f'location{"s" if len(placed) != 1 else ""}" '
        'xmlns="http://www.w3.org/2000/svg">',
        f"<title>{title}: where {len(placed)} cases sit on Earth</title>",
        f'<rect x="0" y="0" width="{MAP_WIDTH}" height="{MAP_HEIGHT}" '
        'fill="var(--gc-map-ocean)"/>',
    ]
    lines.extend(_land())
    lines.extend(_graticule())

    # Extents wide enough to read are outlined first, so markers stay on top.
    for case in placed:
        is_cap = _is_pole_cap(case.extent)
        for x, y, w, h in _extent_boxes(case.extent):
            # A pole cap is a thin band by construction, so the suppression
            # threshold would drop it on height alone. It is drawn because it
            # is a cap, not because it happened to clear a pixel budget.
            if not is_cap and (w < _MIN_EXTENT_PIXELS or h < _MIN_EXTENT_PIXELS):
                continue
            klass = "gc-map-extent gc-map-polar" if is_cap else "gc-map-extent"
            # A group, not attributes on the rect: <title> must be a child
            # element, and grouping keeps an antimeridian split one hoverable
            # unit carrying one identity.
            lines.append(
                f'<g class="gc-map-extent-group" data-case-id="{case.id}">'
                f"<title>{_map_escape(_extent_title(case, is_cap))}</title>"
                f'<rect class="{klass}" x="{_n(x)}" y="{_n(y)}" '
                f'width="{_n(w)}" height="{_n(h)}" {_MAP_EXTENT} '
                'stroke-width="1" fill-opacity="0.35"/></g>'
            )

    points = [(*_extent_centroid(case.extent), case) for case in placed]
    for cluster in _cluster(points):
        members = cluster["cases"]
        count = len(members)
        # The marker grows with the count, but as a square root: area, not
        # radius, should track how many cases are stacked here.
        radius = 3.5 + min(count, 40) ** 0.5
        x, y = _n(cluster["x"]), _n(cluster["y"])
        lines.append(
            f'<g class="gc-map-marker" data-case-ids="'
            f'{" ".join(str(member.id) for member in members)}">'
            f"<title>{_map_escape(_cluster_label(members))}"
            f'</title><circle cx="{x}" cy="{y}" r="{_n(radius)}" {_MAP_MARKER} '
            'fill-opacity="0.75" stroke="var(--gc-map-edge)" stroke-width="1"/>'
        )
        if count > 1:
            lines.append(
                f'<text class="gc-map-count" x="{x}" y="{_n(cluster["y"] + 3)}" '
                f'text-anchor="middle" font-size="9" font-weight="600" '
                f"{_MAP_LABEL}>{count}</text>"
            )
        lines.append("</g>")

    lines.append("</svg>")
    return "".join(lines)


def _map_escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
