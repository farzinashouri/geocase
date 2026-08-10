```python
"""
A small self‑contained module that provides a single function
`segment_intersection(a, b)` for computing the intersection of two
2‑D line segments.

The function accepts each segment as a pair of endpoints:
    ((x1, y1), (x2, y2))

It returns:
    * `None` if the segments do not intersect.
    * `(x, y)` if they intersect at exactly one point.
    * `((xa, ya), (xb, yb))` if they overlap over a non‑zero length,
      giving the endpoints of the shared portion.

The implementation uses `shapely` (version 2.1) for robust geometric
operations. Importing this module has no side effects beyond the
necessary imports.
"""

from __future__ import annotations

from typing import Tuple, Optional, Union

from shapely.geometry import LineString, Point, GeometryCollection

# Type aliases for clarity
Point2D = Tuple[float, float]
Segment2D = Tuple[Point2D, Point2D]
IntersectionResult = Union[None, Point2D, Segment2D]


def segment_intersection(a: Segment2D, b: Segment2D) -> IntersectionResult:
    """
    Compute the intersection of two 2‑D line segments.

    Parameters
    ----------
    a, b : Segment2D
        Each segment is represented as ((x1, y1), (x2, y2)).

    Returns
    -------
    None
        If the segments do not intersect.
    Point2D
        If the segments intersect at exactly one point.
    Segment2D
        If the segments overlap over a non‑zero length.
    """
    # Create shapely LineString objects for the segments
    seg_a = LineString(a)
    seg_b = LineString(b)

    # Compute the intersection geometry
    inter = seg_a.intersection(seg_b)

    # No intersection
    if inter.is_empty:
        return None

    # Intersection is a single point
    if isinstance(inter, Point):
        x, y = inter.coords[0]
        return (float(x), float(y))

    # Intersection is a line segment (overlap)
    if isinstance(inter, LineString):
        coords = list(inter.coords)
        # Ensure we return the endpoints in the same order as the
        # overlapping portion (shapely already provides them in order)
        p1 = (float(coords[0][0]), float(coords[0][1]))
        p2 = (float(coords[-1][0]), float(coords[-1][1]))
        return (p1, p2)

    # For any other geometry type (unlikely for two segments),
    # return None to indicate no usable intersection.
    return None
```