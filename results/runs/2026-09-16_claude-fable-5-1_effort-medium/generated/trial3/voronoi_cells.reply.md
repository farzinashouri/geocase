```python
"""Bounded Voronoi cells for a set of planar points.

`voronoi_cells(points, bounds)` returns, for each input point, the convex
polygon consisting of every location inside the bounding rectangle that is
closer to that point than to any other input point.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from shapely.geometry import GeometryCollection, MultiPoint, Point, Polygon, box
from shapely.ops import voronoi_diagram
from shapely.strtree import STRtree

Coord = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Iterable[Coord], bounds: Bounds) -> List[Polygon]:
    """Return one shapely Polygon per input point, in input order.

    Parameters
    ----------
    points:
        Sequence of N distinct (x, y) tuples in a planar coordinate system.
    bounds:
        (minx, miny, maxx, maxy) rectangle containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        The i-th polygon is the intersection of the rectangle with the
        Voronoi region of the i-th point.
    """
    pts: Sequence[Coord] = [(float(x), float(y)) for x, y in points]
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if minx >= maxx or miny >= maxy:
        raise ValueError("bounds must describe a non-degenerate rectangle")
    clip = box(minx, miny, maxx, maxy)

    n = len(pts)
    if n == 0:
        return []
    if n == 1:
        # A single site owns the entire rectangle.
        return [Polygon(clip.exterior.coords)]

    # Build the unbounded diagram, extended at least as far as the clip
    # rectangle so every cell fully covers its share of the rectangle.
    # A margin around the rectangle keeps GEOS's outer boundary safely
    # outside the region we care about.
    w, h = maxx - minx, maxy - miny
    margin = max(w, h)
    envelope = box(minx - margin, miny - margin, maxx + margin, maxy + margin)
    diagram = voronoi_diagram(MultiPoint(pts), envelope=envelope, tolerance=0.0)

    # Map each raw cell back to its generating site.  A cell's
    # representative point lies strictly inside the cell, and the nearest
    # site to any interior location is, by definition, the cell's own site.
    site_geoms = [Point(p) for p in pts]
    tree = STRtree(site_geoms)

    result: List[Polygon] = [Polygon()] * n
    for raw in _iter_geoms(diagram):
        if raw.is_empty:
            continue
        idx = int(tree.nearest(raw.representative_point()))
        cell = raw.intersection(clip)
        result[idx] = _as_polygon(cell)

    return result


def _iter_geoms(geom):
    """Yield the member geometries of a collection (or the geometry itself)."""
    if isinstance(geom, GeometryCollection) or hasattr(geom, "geoms"):
        for g in geom.geoms:
            yield g
    else:
        yield geom


def _as_polygon(geom) -> Polygon:
    """Coerce a clipped Voronoi cell to a single Polygon.

    Cells are convex and the clip rectangle is convex, so the intersection
    is a single convex polygon (or empty).  Any lower-dimensional slivers
    that could arise from numerical noise are discarded.
    """
    if geom.is_empty:
        return Polygon()
    if isinstance(geom, Polygon):
        return geom
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon) and not g.is_empty]
        if not polys:
            return Polygon()
        return max(polys, key=lambda g: g.area)
    return Polygon()


__all__ = ["voronoi_cells"]
```