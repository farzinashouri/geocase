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

The two paths are captioned differently, and that distinction is not cosmetic:
a page that claims to show real geometry while drawing an archetype is lying
about its own provenance. Rasters and NetCDF remain metadata-only either way.

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

    ``is_real`` distinguishes the two vector paths. It must track what was
    actually drawn: the caption is the only thing on the page telling a reader
    whether they are looking at this case's coordinates or at an archetype.
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
    return f"Schematic: {detail}. Drawn from metadata, not from the pixels."


def _render(case: Any, provider: GeometryProvider | None) -> tuple[str | None, bool]:
    category = str(getattr(case.category, "value", case.category))
    if category == "vector":
        return _vector_render(case, provider)
    if category == "raster":
        return _raster_svg(case), False
    return None, False


def case_diagram(
    case: Any, geometry_provider: GeometryProvider | None = None
) -> list[str]:
    """Return the markdown lines for a case's diagram, or [] if undrawable.

    Callers append this straight into the page body. Returning an empty list
    for the undrawable cases (netcdf, and rasters with no declared shape or
    band count) is intentional -- a placeholder box would assert structure the
    metadata does not actually have.

    Pass ``geometry_provider`` to draw vector cases from their real geometry;
    without it every diagram is metadata-only.
    """
    svg, is_real = _render(case, geometry_provider)
    if svg is None:
        return []

    return [
        '<figure class="gc-figure">',
        svg,
        f"<figcaption>{_caption(case, is_real)}</figcaption>",
        "</figure>",
        "",
    ]


def case_thumbnail(case: Any, geometry_provider: GeometryProvider | None = None) -> str:
    """Return a bare inline SVG for grid/listing use, or "" if undrawable."""
    svg, _ = _render(case, geometry_provider)
    return svg or ""
