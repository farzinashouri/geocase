```python
"""Exact Voronoi cells for planar points, clipped to a bounding rectangle.

The public entry point is :func:`voronoi_cells`.  Importing this module has no
side effects.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import MultiPoint, Polygon, box
from shapely.geometry.base import BaseGeometry

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Iterable[Sequence[float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """Return the Voronoi cells of ``points``, clipped to ``bounds``.

    Parameters
    ----------
    points:
        Iterable of ``N`` distinct ``(x, y)`` pairs in a projected (planar)
        coordinate system.
    bounds:
        ``(minx, miny, maxx, maxy)`` rectangle that contains all the points.

    Returns
    -------
    list of shapely.Polygon
        A list of length ``N``; element ``i`` is exactly the subset of the
        ``bounds`` rectangle whose locations are strictly closer to
        ``points[i]`` than to any other input point (plus the shared
        boundaries, which have zero area).  A point lying outside ``bounds``
        yields an empty polygon.
    """
    coords = _as_coords(points)
    clip = _as_box(bounds)

    if len(coords) == 1:
        return [clip]

    cells = _raw_cells(coords, clip)
    return [_polygonal(shapely.intersection(cell, clip)) for cell in cells]


# --------------------------------------------------------------------------
# input handling
# --------------------------------------------------------------------------


def _as_coords(points: Iterable[Sequence[float]]) -> np.ndarray:
    """Validate the input sites and return them as an ``(N, 2)`` float array."""
    coords = np.asarray(list(points), dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if len(coords) == 0:
        raise ValueError("points must contain at least one point")
    if not np.isfinite(coords).all():
        raise ValueError("points must contain only finite coordinates")
    if len(np.unique(coords, axis=0)) != len(coords):
        raise ValueError("points must be distinct")
    return coords


def _as_box(bounds: Tuple[float, float, float, float]) -> Polygon:
    """Validate ``bounds`` and return it as a rectangular polygon."""
    values = np.asarray(bounds, dtype=float)
    if values.shape != (4,):
        raise ValueError("bounds must be a (minx, miny, maxx, maxy) tuple")
    if not np.isfinite(values).all():
        raise ValueError("bounds must contain only finite coordinates")
    minx, miny, maxx, maxy = values
    if minx >= maxx or miny >= maxy:
        raise ValueError("bounds must have positive width and height")
    return box(minx, miny, maxx, maxy)


# --------------------------------------------------------------------------
# diagram construction
# --------------------------------------------------------------------------


def _raw_cells(coords: np.ndarray, clip: Polygon) -> List[BaseGeometry]:
    """Return the unclipped Voronoi cells, in the same order as ``coords``."""
    sites = MultiPoint(coords)
    extend_to = _extend_to(coords, clip)

    # GEOS >= 3.12 can emit the cells already aligned with the input points.
    try:
        collection = shapely.voronoi_polygons(
            sites, extend_to=extend_to, ordered=True
        )
        cells = list(shapely.get_parts(collection))
        if len(cells) == len(coords):
            return cells
    except Exception:
        pass

    # Otherwise recover the ordering ourselves: every site lies in the interior
    # of its own cell, and cell interiors are disjoint.
    collection = shapely.voronoi_polygons(sites, extend_to=extend_to)
    return _match_cells_to_sites(list(shapely.get_parts(collection)), coords)


def _extend_to(coords: np.ndarray, clip: Polygon) -> Polygon:
    """A rectangle comfortably larger than both the sites and the clip box.

    Unbounded cells are truncated by GEOS to this envelope, so it has to
    contain the clip rectangle with room to spare for the clipped result to be
    exact.
    """
    minx, miny, maxx, maxy = clip.bounds
    minx = min(minx, float(coords[:, 0].min()))
    maxx = max(maxx, float(coords[:, 0].max()))
    miny = min(miny, float(coords[:, 1].min()))
    maxy = max(maxy, float(coords[:, 1].max()))
    pad = max(maxx - minx, maxy - miny, 1.0)
    return box(minx - pad, miny - pad, maxx + pad, maxy + pad)


def _match_cells_to_sites(
    cells: List[BaseGeometry], coords: np.ndarray
) -> List[BaseGeometry]:
    """Reorder ``cells`` so that cell ``i`` is the cell containing site ``i``."""
    if len(cells) != len(coords):
        raise RuntimeError(
            f"Voronoi construction produced {len(cells)} cells "
            f"for {len(coords)} points"
        )

    tree = STRtree(cells)
    sites = shapely.points(coords)
    ordered: List[BaseGeometry] = []
    used: set = set()

    for site in sites:
        candidates = [int(j) for j in tree.query(site, predicate="intersects")]
        free = [j for j in candidates if j not in used] or candidates
        if not free:
            # No overlap at all (should not happen): fall back to proximity.
            free = [int(np.argmin([shapely.distance(site, c) for c in cells]))]
        if len(free) > 1:
            # Prefer the cell the site sits deepest inside of.
            free.sort(
                key=lambda j: shapely.distance(site, shapely.get_exterior_ring(cells[j])),
                reverse=True,
            )
        chosen = free[0]
        used.add(chosen)
        ordered.append(cells[chosen])

    if len(used) != len(cells):
        raise RuntimeError("could not match Voronoi cells to input points")
    return ordered


# --------------------------------------------------------------------------
# result cleanup
# --------------------------------------------------------------------------


def _polygonal(geom: BaseGeometry) -> Polygon:
    """Coerce an intersection result to a single ``Polygon``.

    A Voronoi cell and the clip rectangle are both convex, so the intersection
    is a single convex polygon, a zero-area sliver, or empty.  The latter two
    are reported as an empty polygon.
    """
    parts = [g for g in _flatten(geom) if isinstance(g, Polygon) and not g.is_empty]
    if not parts:
        return Polygon()
    if len(parts) == 1:
        return parts[0]
    merged = shapely.union_all(parts)
    if isinstance(merged, Polygon):
        return merged
    return max(parts, key=lambda g: g.area)


def _flatten(geom: BaseGeometry) -> List[BaseGeometry]:
    """Recursively expand multi-part and collection geometries."""
    if geom is None or geom.is_empty:
        return []
    parts = shapely.get_parts(geom)
    if len(parts) == 1 and parts[0] == geom:
        return [geom]
    if len(parts) == 0:
        return [geom]
    flat: List[BaseGeometry] = []
    for part in parts:
        if part.geom_type in ("GeometryCollection", "MultiPolygon", "MultiLineString", "MultiPoint"):
            flat.extend(_flatten(part))
        else:
            flat.append(part)
    return flat
```