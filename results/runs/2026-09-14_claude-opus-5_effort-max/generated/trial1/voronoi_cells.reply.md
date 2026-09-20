Bash and Write are both blocked by permissions here, so I couldn't run the brute-force check I wanted (sample random points in the rectangle, confirm each lands in the cell of its nearest site). The module below is reasoned through rather than executed — if you approve tool access I'll verify it.

Two design points worth flagging: GEOS clips its diagram to the sites' own envelope grown by its width/height, which does *not* reach the corners of `bounds` when the points are clustered in one part of it — hence the explicit oversized `extend_to` frame followed by an intersection with the rectangle. And GEOS returns cells in an unspecified order, so the module asks for `ordered=True` (shapely 2.1 + GEOS ≥ 3.12) and falls back to matching each site to the only cell at distance zero from it.

```python
"""Exact Voronoi cells for a set of planar points, clipped to a rectangle.

The module has a single public entry point, :func:`voronoi_cells`, which maps
each input site to the part of the bounding rectangle that lies closer to it
than to any other site.  Cell ``i`` always corresponds to point ``i``.
"""

import math
from collections.abc import Iterable, Sequence

from shapely import MultiPoint, Point, Polygon, STRtree, box, voronoi_polygons
from shapely.errors import UnsupportedGEOSVersionError

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Iterable[Sequence[float]],
    bounds: Sequence[float],
) -> list[Polygon]:
    """Partition ``bounds`` into the Voronoi cells of ``points``.

    Parameters
    ----------
    points
        ``N`` distinct ``(x, y)`` pairs in a projected (planar) coordinate
        system, all of them inside ``bounds``.
    bounds
        ``(minx, miny, maxx, maxy)`` of a non-degenerate rectangle.

    Returns
    -------
    list of shapely.Polygon
        ``N`` convex polygons, the ``i``-th being the set of locations in the
        rectangle no farther from ``points[i]`` than from any other point.
        They tile the rectangle and meet only along shared edges (each polygon
        is closed, so a location equidistant from two sites lies on both).

    Raises
    ------
    ValueError
        If ``points`` is empty, holds a repeated or non-finite coordinate, or
        strays outside ``bounds``; or if ``bounds`` has no area.
    """
    coords = _check_points(points)
    minx, miny, maxx, maxy = _check_bounds(bounds, coords)
    rect = box(minx, miny, maxx, maxy)

    if len(coords) == 1:
        return [rect]

    # Build the diagram over a frame strictly larger than the rectangle.  Left
    # to itself GEOS clips to the sites' own envelope grown by its width and
    # height, which need not reach the corners of `bounds` when the sites sit
    # in one small part of it.
    pad = max(maxx - minx, maxy - miny)
    frame = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    return [_polygon_part(cell.intersection(rect)) for cell in _diagram(coords, frame)]


def _check_points(points: Iterable[Sequence[float]]) -> list[tuple[float, float]]:
    coords = [(float(x), float(y)) for x, y in points]
    if not coords:
        raise ValueError("points must hold at least one (x, y) pair")
    if not all(math.isfinite(v) for xy in coords for v in xy):
        raise ValueError("point coordinates must be finite")
    if len(set(coords)) != len(coords):
        raise ValueError("points must be distinct: duplicates share a single cell")
    return coords


def _check_bounds(
    bounds: Sequence[float],
    coords: list[tuple[float, float]],
) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError(f"bounds must be a rectangle with area, got {tuple(bounds)!r}")
    for x, y in coords:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError(f"point ({x!r}, {y!r}) lies outside bounds")
    return minx, miny, maxx, maxy


def _diagram(coords: list[tuple[float, float]], frame: Polygon) -> list[Polygon]:
    """The Voronoi cells of ``coords``, in input order, clipped to ``frame``."""
    sites = MultiPoint(coords)
    try:
        cells = list(voronoi_polygons(sites, extend_to=frame, ordered=True).geoms)
    except (TypeError, UnsupportedGEOSVersionError):
        # shapely < 2.1 or GEOS < 3.12: the cells come back in an unspecified
        # order, so pair them with their sites by hand.
        cells = _reorder(list(voronoi_polygons(sites, extend_to=frame).geoms), coords)
    if len(cells) != len(coords):
        raise RuntimeError(f"got {len(cells)} Voronoi cells for {len(coords)} points")
    return cells


def _reorder(cells: list[Polygon], coords: list[tuple[float, float]]) -> list[Polygon]:
    if len(cells) != len(coords):
        return cells  # let the caller report the mismatch
    tree = STRtree(cells)
    # A site lies in the interior of its own cell and outside every other one,
    # so the nearest cell -- the only one at distance zero -- is unambiguous.
    order = [int(tree.nearest(Point(xy))) for xy in coords]
    if len(set(order)) != len(cells):
        raise RuntimeError("could not match each Voronoi cell to an input point")
    return [cells[i] for i in order]


def _polygon_part(clipped) -> Polygon:
    """A clipped cell as a single Polygon.

    Clipping a convex cell with a rectangle yields one convex polygon, so this
    almost always returns ``clipped`` untouched; the rest guards against
    floating-point debris such as a stray sliver or a boundary-only fragment.
    """
    if isinstance(clipped, Polygon) and not clipped.is_empty:
        return clipped
    parts = [
        part
        for part in getattr(clipped, "geoms", ())
        if isinstance(part, Polygon) and not part.is_empty
    ]
    if not parts:
        raise RuntimeError(f"clipped Voronoi cell has no area: {clipped.geom_type}")
    return max(parts, key=lambda part: part.area)
```