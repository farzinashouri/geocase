"""Bounded Voronoi (Thiessen) cells for a set of planar points.

``voronoi_cells(points, bounds)`` returns one shapely Polygon per input point,
in input order, each being the exact region of the bounding rectangle whose
locations are nearer to that point than to any other input point.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

import shapely
from shapely.geometry import MultiPoint, Polygon, box

__all__ = ["voronoi_cells"]

Point2D = Tuple[float, float]


def voronoi_cells(
    points: Iterable[Point2D],
    bounds: Sequence[float],
) -> List[Polygon]:
    """Compute the Voronoi diagram of ``points`` clipped to ``bounds``.

    Parameters
    ----------
    points:
        Iterable of N distinct ``(x, y)`` tuples in a projected (planar) CRS.
    bounds:
        Rectangle ``(minx, miny, maxx, maxy)`` containing all the points.

    Returns
    -------
    list of shapely.geometry.Polygon
        N polygons; element ``i`` is the part of the rectangle closer to
        ``points[i]`` than to any other input point. The polygons tile the
        rectangle and overlap only along their shared boundaries.
    """
    coords = [(float(x), float(y)) for x, y in points]
    if not coords:
        return []

    minx, miny, maxx, maxy = (float(v) for v in bounds)
    if maxx <= minx or maxy <= miny:
        raise ValueError("bounds must be a non-degenerate (minx, miny, maxx, maxy) rectangle")

    envelope = box(minx, miny, maxx, maxy)

    if len(set(coords)) != len(coords):
        raise ValueError("points must be distinct")
    for x, y in coords:
        if not (minx <= x <= maxx and miny <= y <= maxy):
            raise ValueError("every point must lie inside bounds")

    # A single site owns the whole rectangle; shapely emits no cells for N == 1.
    if len(coords) == 1:
        return [envelope]

    sites = MultiPoint(coords)
    # ordered=True makes cell i correspond to input point i. extend_to pushes the
    # unbounded cells past the rectangle so the clip below is exact rather than
    # truncated at shapely's default (slightly padded) diagram extent.
    cells = shapely.voronoi_polygons(sites, extend_to=envelope, ordered=True)

    clipped: List[Polygon] = []
    for cell in cells.geoms:
        piece = cell.intersection(envelope)
        # Intersecting a convex cell with a rectangle yields a convex polygon,
        # but guard against slivers from floating-point boundary contact.
        if piece.geom_type != "Polygon":
            parts = [g for g in getattr(piece, "geoms", []) if g.geom_type == "Polygon"]
            if not parts:
                raise ValueError("degenerate Voronoi cell produced for the given inputs")
            piece = max(parts, key=lambda g: g.area)
        clipped.append(piece)

    if len(clipped) != len(coords):
        raise ValueError("unexpected number of Voronoi cells; are the points distinct?")

    return clipped