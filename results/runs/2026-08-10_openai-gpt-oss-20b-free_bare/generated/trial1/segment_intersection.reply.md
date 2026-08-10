```python
"""
A tiny module providing a robust intersection routine for 2‑D line segments.
"""

from __future__ import annotations

from typing import Tuple, Optional, Union

from shapely.geometry import LineString, Point, GeometryCollection

# Type aliases for clarity
Segment = Tuple[Tuple[float, float], Tuple[float, float]]
Point2D = Tuple[float, float]
Intersection = Union[None, Point2D, Segment]


def segment_intersection(a: Segment, b: Segment) -> Intersection:
    """
    Compute the intersection of two 2‑D line segments.

    Parameters
    ----------
    a, b : Segment
        Each segment is represented as ((x1, y1), (x2, y2)).

    Returns
    -------
    None
        If the segments do not intersect.
    Point2D
        If the segments intersect at exactly one point.
    Segment
        If the segments overlap over a non‑zero length.
    """
    # Create shapely LineString objects
    ls_a = LineString(a)
    ls_b = LineString(b)

    inter = ls_a.intersection(ls_b)

    if inter.is_empty:
        return None

    # Handle simple cases directly
    if isinstance(inter, Point):
        return (inter.x, inter.y)

    if isinstance(inter, LineString):
        coords = list(inter.coords)
        return (coords[0], coords[-1])

    # For robustness, handle collections that may arise from degenerate cases
    if isinstance(inter, GeometryCollection):
        # Prefer a point if present, otherwise a line
        for geom in inter.geoms:
            if isinstance(geom, Point):
                return (geom.x, geom.y)
        for geom in inter.geoms:
            if isinstance(geom, LineString):
                coords = list(geom.coords)
                return (coords[0], coords[-1])

    # Fallback: if we somehow get a MultiPoint or MultiLineString
    if hasattr(inter, "geoms"):
        for geom in inter.geoms:
            if isinstance(geom, Point):
                return (geom.x, geom.y)
        for geom in inter.geoms:
            if isinstance(geom, LineString):
                coords = list(geom.coords)
                return (coords[0], coords[-1])

    # If all else fails, return None
    return None
```