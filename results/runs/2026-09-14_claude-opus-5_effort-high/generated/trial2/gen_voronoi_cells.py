"""Bounded Voronoi cells for a set of planar points.

The public entry point is :func:`voronoi_cells`, which returns one polygon per
input point: the part of the bounding rectangle that is closer to that point
than to any other input point.

Importing this module has no side effects.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, box
from shapely.strtree import STRtree

__all__ = ["voronoi_cells"]


def voronoi_cells(
    points: Sequence[Tuple[float, float]],
    bounds: Tuple[float, float, float, float],
) -> List[Polygon]:
    """Compute bounded Voronoi cells for ``points`` clipped to ``bounds``.

    Parameters
    ----------
    points:
        Sequence of ``N`` distinct ``(x, y)`` tuples in a projected (planar)
        coordinate system. Every point must lie within ``bounds``.
    bounds:
        Rectangle ``(minx, miny, maxx, maxy)`` containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        A list of length ``N``; element ``i`` is exactly the set of locations
        inside the rectangle that are closer to ``points[i]`` than to any other
        input point. The cells tile the rectangle and overlap only along their
        shared boundaries.

    Raises
    ------
    ValueError
        If ``points`` is malformed, contains non-finite or duplicate
        coordinates, if ``bounds`` is degenerate, or if a point lies outside
        ``bounds``.
    """
    coords = np.asarray(points, dtype=float)
    if coords.size == 0:
        return []
    if coords.ndim != 2 or coords.shape[1] != 2:
        raise ValueError("points must be a sequence of (x, y) pairs")
    if not np.isfinite(coords).all():
        raise ValueError("points must have finite coordinates")

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if not (minx < maxx and miny < maxy):
        raise ValueError(
            "bounds must be a non-degenerate (minx, miny, maxx, maxy) rectangle"
        )
    envelope = box(minx, miny, maxx, maxy)

    if np.unique(coords, axis=0).shape[0] != coords.shape[0]:
        raise ValueError("points must be distinct")

    inside = (
        (coords[:, 0] >= minx)
        & (coords[:, 0] <= maxx)
        & (coords[:, 1] >= miny)
        & (coords[:, 1] <= maxy)
    )
    if not inside.all():
        raise ValueError("every point must lie within bounds")

    # A single site owns the whole rectangle; GEOS has no diagram to build.
    if coords.shape[0] == 1:
        return [envelope]

    # Build the raw (unclipped) diagram. `extend_to` pushes the clipping
    # envelope GEOS uses well beyond the target rectangle, so that every
    # unbounded cell fully covers its share of `bounds` before we clip.
    pad = 10.0 * max(maxx - minx, maxy - miny)
    extend_to = box(minx - pad, miny - pad, maxx + pad, maxy + pad)
    regions = list(
        shapely.get_parts(
            shapely.voronoi_polygons(shapely.multipoints(coords), extend_to=extend_to)
        )
    )
    if not regions:
        raise RuntimeError("GEOS returned an empty Voronoi diagram")

    # GEOS does not guarantee that the regions come back in input order, so
    # match each site to the region containing it. A site lies strictly inside
    # its own cell and outside every other cell, so the match is unique.
    sites = shapely.points(coords)
    tree = STRtree(regions)
    site_idx, region_idx = tree.query(sites, predicate="intersects")

    assigned = np.full(coords.shape[0], -1, dtype=np.int64)
    for s, r in zip(site_idx, region_idx):
        if assigned[s] == -1:
            assigned[s] = r

    # Defensive fallback for the (near-)degenerate cases where a robustness
    # wobble leaves a site just off its own region.
    missing = np.flatnonzero(assigned == -1)
    if missing.size:
        assigned[missing] = np.asarray(tree.nearest(sites[missing]), dtype=np.int64)

    return [_as_polygon(envelope.intersection(regions[r])) for r in assigned]


def _as_polygon(geom) -> Polygon:
    """Coerce a clipped cell to a single Polygon.

    Clipping a convex Voronoi region with a rectangle is convex, so this is a
    plain Polygon in practice; the collection handling is a guard against GEOS
    emitting stray zero-area pieces in degenerate configurations.
    """
    if isinstance(geom, Polygon):
        if geom.is_empty:
            raise RuntimeError("clipped Voronoi cell is empty")
        return geom

    parts = [
        g
        for g in getattr(geom, "geoms", ())
        if isinstance(g, Polygon) and not g.is_empty
    ]
    if not parts:
        raise RuntimeError(
            f"clipped Voronoi cell has no polygonal part (got {geom.geom_type})"
        )
    return max(parts, key=lambda g: g.area)