"""Project a case's real geometry into the catalog schematic viewport.

Kept separate from :mod:`catalog_svg` on purpose. ``catalog_svg`` stays
dependency-free and importable from a plain checkout; everything here needs a
loaded GeoDataFrame, which means shapely and geopandas. The generator wires the
two together (see ``generate_catalog_pages.py``); either half is testable
without the other.

Two properties are load-bearing:

- **Coordinates are rounded to a fixed 2 decimals.** Unrounded floats make the
  committed pages churn on platform FP noise, which would turn the
  ``--check`` gate from a signal into a nuisance.
- **Any load failure is the caller's problem to absorb.** ``unclosed_ring_polygon``
  is *supposed* to be malformed, and Plan 28 adds more like it, so the provider
  built by :func:`geometry_provider` swallows every exception and returns
  ``None`` -- the caller then falls back to the metadata archetype.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


#: Decimals kept in emitted path coordinates. See the module docstring.
PRECISION = 2

#: Inset from the viewport edge, so a shape never touches the frame.
MARGIN = 10

#: Span substituted for a degenerate extent (a single point, a zero-width
#: bbox). Any positive value works -- it exists only to avoid dividing by zero.
_NOMINAL_SPAN = 1.0


def _fmt(value: float) -> str:
    """Format one coordinate, dropping a trailing ``.0`` so paths stay short."""
    text = f"{value:.{PRECISION}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


class _Projector:
    """Map world coordinates into the viewport, preserving aspect ratio."""

    def __init__(
        self, bounds: tuple[float, float, float, float], width: int, height: int
    ) -> None:
        minx, miny, maxx, maxy = bounds
        span_x = maxx - minx or _NOMINAL_SPAN
        span_y = maxy - miny or _NOMINAL_SPAN

        inner_w = width - 2 * MARGIN
        inner_h = height - 2 * MARGIN
        # One scale for both axes: a per-axis scale would silently un-skew a
        # thin corridor into a square, which is exactly the shape a reader
        # looking at ``thin_corridor_shape`` needs to see.
        self._scale = min(inner_w / span_x, inner_h / span_y)

        self._minx = minx
        self._miny = miny
        # Centre the drawn extent in whichever axis has slack.
        self._dx = MARGIN + (inner_w - span_x * self._scale) / 2
        self._dy = MARGIN + (inner_h - span_y * self._scale) / 2
        self._height = height

    def __call__(self, x: float, y: float) -> tuple[float, float]:
        px = self._dx + (x - self._minx) * self._scale
        # SVG y grows downward; geographic y grows upward.
        py = self._height - (self._dy + (y - self._miny) * self._scale)
        return px, py


def _ring_path(project: Any, coords: Any) -> str:
    points = [project(float(x), float(y)) for x, y in (c[:2] for c in coords)]
    if not points:
        return ""
    head = f"M {_fmt(points[0][0])} {_fmt(points[0][1])}"
    tail = "".join(f" L {_fmt(x)} {_fmt(y)}" for x, y in points[1:])
    return head + tail


def _geometry_parts(geometry: Any) -> list[Any]:
    """Flatten a geometry into its single-part components."""
    geoms = getattr(geometry, "geoms", None)
    if geoms is None:
        return [geometry]
    parts: list[Any] = []
    for part in geoms:
        parts.extend(_geometry_parts(part))
    return parts


def geometry_shapes(
    gdf: Any,
    width: int,
    height: int,
    *,
    point_attrs: str = "",
    line_attrs: str = "",
    area_attrs: str = "",
) -> list[str] | None:
    """Render a GeoDataFrame's geometries as SVG elements, or ``None``.

    ``None`` means "nothing drawable" -- an empty frame, all-null geometry, or
    an unusable extent -- and the caller should fall back to the archetype.
    The ``*_attrs`` strings carry the presentation (fill, stroke, radius) so
    this module stays free of any colour or theme knowledge.
    """
    if gdf is None or len(gdf) == 0:
        return None

    try:
        geometries = [g for g in gdf.geometry if g is not None and not g.is_empty]
    except Exception:
        return None
    if not geometries:
        return None

    bounds = gdf.geometry.total_bounds
    if any(
        value != value or value in (float("inf"), float("-inf")) for value in bounds
    ):
        return None

    project = _Projector(
        (float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])),
        width,
        height,
    )

    shapes: list[str] = []
    for geometry in geometries:
        for part in _geometry_parts(geometry):
            kind = part.geom_type
            if kind == "Point":
                x, y = project(float(part.x), float(part.y))
                shapes.append(f'<circle cx="{_fmt(x)}" cy="{_fmt(y)}" {point_attrs}/>')
            elif kind == "LineString":
                path = _ring_path(project, list(part.coords))
                if path:
                    shapes.append(f'<path d="{path}" {line_attrs}/>')
            elif kind == "LinearRing":
                path = _ring_path(project, list(part.coords))
                if path:
                    shapes.append(f'<path d="{path} Z" {area_attrs}/>')
            elif kind == "Polygon":
                # Exterior and interiors go in one path so ``fill-rule="evenodd"``
                # (supplied by the caller in ``area_attrs``) renders holes as
                # actual holes rather than as overpainted rings.
                segments = [_ring_path(project, list(part.exterior.coords)) + " Z"]
                for interior in part.interiors:
                    segments.append(_ring_path(project, list(interior.coords)) + " Z")
                shapes.append(f'<path d="{" ".join(segments)}" {area_attrs}/>')

    return shapes or None


def geometry_provider(loader: Callable[[str], Any]) -> Callable[[str], Any]:
    """Wrap a case loader so any failure degrades to the archetype fallback.

    Results are cached per case id: the generator draws each case several times
    across the index, its hubs, and its own page, and a reload per draw would
    make a docs regeneration measurably slower for no gain.
    """
    cache: dict[str, Any] = {}

    def provide(case_id: str) -> Any:
        if case_id not in cache:
            try:
                cache[case_id] = loader(case_id)
            except Exception:
                cache[case_id] = None
        return cache[case_id]

    return provide
