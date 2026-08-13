"""Compute a good anchor point for drawing a text label inside a polygon.

The main entry point is :func:`label_point`, which returns a shapely
``Point`` guaranteed to lie inside the given ``Polygon``.

Strategy
--------
1. If the polygon's centroid falls inside the polygon, use it — it is the
   most natural label anchor for convex-ish shapes.
2. Otherwise (concave, ring-like, or multi-lobed shapes), use the "pole of
   inaccessibility" (``shapely.ops.polylabel``): the interior point farthest
   from the boundary, which gives labels the most surrounding room.
3. As a last resort, fall back to ``representative_point()``, which shapely
   guarantees to be inside the polygon.

Every candidate is checked for containment before being returned, so the
result always satisfies ``polygon.contains(point)`` (for valid, non-empty
polygons).
"""

from __future__ import annotations

from shapely.geometry import Point, Polygon
from shapely.ops import polylabel
from shapely.validation import make_valid

__all__ = ["label_point"]


def _polylabel_tolerance(polygon: Polygon) -> float:
    """Pick a polylabel tolerance proportional to the polygon's size.

    Using a fraction of the shorter bounding-box side keeps the algorithm
    fast while remaining accurate for any coordinate system (degrees,
    meters, pixels, ...).
    """
    minx, miny, maxx, maxy = polygon.bounds
    size = min(maxx - minx, maxy - miny)
    if size <= 0.0:
        # Degenerate bounds; polylabel would not help anyway.
        return 1.0
    return size / 100.0


def label_point(polygon: Polygon) -> Point:
    """Return a Point inside *polygon* suitable for anchoring a text label.

    Parameters
    ----------
    polygon:
        A shapely ``Polygon`` in any coordinate system. Must be non-empty.

    Returns
    -------
    Point
        A point strictly inside the polygon.

    Raises
    ------
    TypeError
        If *polygon* is not a shapely ``Polygon``.
    ValueError
        If *polygon* is empty or has no interior area.
    """
    if not isinstance(polygon, Polygon):
        raise TypeError(
            f"label_point expects a shapely Polygon, got {type(polygon).__name__}"
        )
    if polygon.is_empty:
        raise ValueError("label_point requires a non-empty polygon")

    # Repair invalid geometry (self-intersections etc.) for the geometric
    # tests below, but keep working with polygons only.
    working = polygon
    if not working.is_valid:
        repaired = make_valid(working)
        # make_valid may return a MultiPolygon/GeometryCollection; keep the
        # largest polygonal piece as the label target.
        candidates = [
            geom
            for geom in getattr(repaired, "geoms", [repaired])
            if isinstance(geom, Polygon) and not geom.is_empty
        ]
        if candidates:
            working = max(candidates, key=lambda g: g.area)

    if working.area <= 0.0:
        raise ValueError("label_point requires a polygon with non-zero area")

    # 1) Centroid, when it happens to be inside — the nicest-looking anchor.
    centroid = working.centroid
    if working.contains(centroid):
        return centroid

    # 2) Pole of inaccessibility — deepest interior point, ideal for labels
    #    on concave or ring-shaped polygons.
    try:
        pole = polylabel(working, tolerance=_polylabel_tolerance(working))
        if working.contains(pole):
            return pole
    except Exception:
        pass  # fall through to the guaranteed fallback

    # 3) Guaranteed-interior fallback.
    return working.representative_point()
