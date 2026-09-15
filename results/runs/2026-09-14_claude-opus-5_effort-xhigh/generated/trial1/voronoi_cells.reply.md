I couldn't run a verification script here (Bash needs approval in this session), so the module below is written to be defensive: it uses the GEOS diagram when available and falls back to an exact half-plane construction for any cell it can't match or clip cleanly.

```python
"""Exact planar Voronoi cells, clipped to a bounding rectangle.

The public entry point is :func:`voronoi_cells`.  Importing this module has no
side effects.
"""

from __future__ import annotations

import math
from typing import Iterator, List, Optional, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.errors import GEOSException
from shapely.geometry import MultiPoint, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["voronoi_cells"]

XY = Tuple[float, float]
Bounds = Tuple[float, float, float, float]


def voronoi_cells(points: Sequence[XY], bounds: Bounds) -> List[Polygon]:
    """Return the Voronoi cell of every point, clipped to ``bounds``.

    Parameters
    ----------
    points:
        ``N`` distinct ``(x, y)`` pairs in a projected (planar) coordinate
        system, all of them inside ``bounds``.
    bounds:
        ``(minx, miny, maxx, maxy)``, in the same coordinate system.

    Returns
    -------
    list of shapely.Polygon
        One polygon per input point, **in input order**.  Cell ``i`` is exactly
        the part of the ``bounds`` rectangle that is closer to ``points[i]``
        than to any other input point.  Since the cells are closed, adjacent
        cells share their common boundary (the locus of points equidistant from
        two sites); their interiors are disjoint and together they tile the
        rectangle.

    Raises
    ------
    ValueError
        If ``points`` is not an ``(N, 2)`` array of finite distinct
        coordinates, if ``bounds`` is not a non-degenerate rectangle, or if any
        point lies outside ``bounds``.
    """
    coords = _as_xy_array(points)
    minx, miny, maxx, maxy = _as_bounds(bounds)
    rect = box(minx, miny, maxx, maxy)

    n = len(coords)
    if n == 0:
        return []

    outside = (
        (coords[:, 0] < minx)
        | (coords[:, 0] > maxx)
        | (coords[:, 1] < miny)
        | (coords[:, 1] > maxy)
    )
    if outside.any():
        raise ValueError(f"{int(outside.sum())} point(s) lie outside bounds")

    if n == 1:
        return [rect]

    cells: List[Optional[Polygon]] = [None] * n
    for index, cell in _geos_cells(coords, rect):
        cells[index] = cell

    # Whatever GEOS could not deliver -- or delivered as an unusable geometry --
    # is recomputed straight from the definition of a Voronoi cell.
    ring = np.array(
        [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)], dtype=float
    )
    return [
        cell if cell is not None else _bisector_cell(coords, i, ring)
        for i, cell in enumerate(cells)
    ]


def _geos_cells(coords: np.ndarray, rect: Polygon) -> Iterator[Tuple[int, Polygon]]:
    """Yield ``(point_index, clipped_cell)`` pairs from the GEOS diagram.

    GEOS returns the cells in an arbitrary order, so each one is matched back to
    the site it belongs to: a site lies strictly inside its own cell and
    strictly outside every other, which makes the match unambiguous.
    """
    minx, miny, maxx, maxy = rect.bounds
    # Grow the diagram well past the rectangle so that its cells are guaranteed
    # to cover the whole rectangle before clipping.
    pad = max(maxx - minx, maxy - miny)
    envelope = box(minx - pad, miny - pad, maxx + pad, maxy + pad)

    try:
        diagram = shapely.voronoi_polygons(MultiPoint(coords), extend_to=envelope)
        raw = [g for g in diagram.geoms if isinstance(g, Polygon) and not g.is_empty]
    except (GEOSException, ValueError):
        return
    if not raw:
        return

    tree = STRtree(raw)
    site_index, cell_index = tree.query(shapely.points(coords), predicate="intersects")

    matched_sites: set = set()
    matched_cells: set = set()
    for site, cell in zip(site_index.tolist(), cell_index.tolist()):
        if site in matched_sites or cell in matched_cells:
            continue
        clipped = _single_polygon(raw[cell].intersection(rect))
        if clipped is None:
            continue  # leave this site for the fallback path
        matched_sites.add(site)
        matched_cells.add(cell)
        yield site, clipped


def _single_polygon(geom: BaseGeometry) -> Optional[Polygon]:
    """Reduce an intersection result to one non-empty Polygon, if it has one."""
    if isinstance(geom, Polygon):
        return None if geom.is_empty else geom
    parts = [
        g for g in getattr(geom, "geoms", ()) if isinstance(g, Polygon) and not g.is_empty
    ]
    if not parts:
        return None
    # A convex cell met with a rectangle is connected; extra parts would only be
    # precision slivers, so keep the real one.
    return max(parts, key=lambda g: g.area)


def _bisector_cell(coords: np.ndarray, i: int, ring: np.ndarray) -> Polygon:
    """Build cell ``i`` by clipping ``ring`` with one bisector per other site.

    O(N) per call and exact by construction; used only as a fallback.
    """
    site = coords[i]
    poly = ring
    for j, other in enumerate(coords):
        if j == i:
            continue
        # Closer to `site` than to `other`  <=>  2 (other - site) . x <= |other|^2 - |site|^2
        normal = 2.0 * (other - site)
        offset = float(other @ other - site @ site)
        poly = _clip_halfplane(poly, normal, offset)
        if len(poly) < 3:
            break
    return Polygon(poly) if len(poly) >= 3 else Polygon()


def _clip_halfplane(poly: np.ndarray, normal: np.ndarray, offset: float) -> np.ndarray:
    """Sutherland-Hodgman clip of a convex ring to ``normal . x <= offset``."""
    if len(poly) == 0:
        return poly
    slack = offset - poly @ normal
    inside = slack >= 0.0
    if inside.all():
        return poly
    if not inside.any():
        return poly[:0]

    clipped = []
    for k in range(len(poly)):
        nxt = (k + 1) % len(poly)
        if inside[k]:
            clipped.append(poly[k])
        if inside[k] != inside[nxt]:
            t = slack[k] / (slack[k] - slack[nxt])
            clipped.append(poly[k] + t * (poly[nxt] - poly[k]))
    return np.asarray(clipped, dtype=float)


def _as_xy_array(points: Sequence[XY]) -> np.ndarray:
    """Validate the sites and return them as an ``(N, 2)`` float array."""
    try:
        arr = np.asarray(points, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("points must be a sequence of (x, y) pairs") from None
    if arr.size == 0:
        return np.empty((0, 2), dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if not np.isfinite(arr).all():
        raise ValueError("points must have finite coordinates")
    if len(np.unique(arr, axis=0)) != len(arr):
        raise ValueError("points must be distinct")
    return arr


def _as_bounds(bounds: Bounds) -> Bounds:
    """Validate ``(minx, miny, maxx, maxy)`` and return it as floats."""
    try:
        minx, miny, maxx, maxy = (float(v) for v in bounds)
    except (TypeError, ValueError):
        raise ValueError("bounds must be (minx, miny, maxx, maxy)") from None
    if not all(math.isfinite(v) for v in (minx, miny, maxx, maxy)):
        raise ValueError("bounds must have finite coordinates")
    if not (minx < maxx and miny < maxy):
        raise ValueError("bounds must be a non-degenerate rectangle")
    return minx, miny, maxx, maxy
```