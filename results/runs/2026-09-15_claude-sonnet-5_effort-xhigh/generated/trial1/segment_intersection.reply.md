```python
"""Compute the intersection of two 2D line segments."""

from typing import Tuple, Union

from shapely.geometry import LineString, Point

Point2D = Tuple[float, float]
Segment = Tuple[Point2D, Point2D]
Intersection = Union[None, Point2D, Segment]


def _to_geometry(segment: Segment):
    p1, p2 = segment
    if p1 == p2:
        return Point(p1)
    return LineString([p1, p2])


def segment_intersection(a: Segment, b: Segment) -> Intersection:
    """Return the shared portion of two segments.

    Returns None if the segments share no point, an (x, y) point if they
    share exactly one point, or a segment ((xa, ya), (xb, yb)) if they
    overlap along more than one point.
    """
    geom_a = _to_geometry(a)
    geom_b = _to_geometry(b)
    inter = geom_a.intersection(geom_b)

    if inter.is_empty:
        return None

    if inter.geom_type == "Point":
        return (inter.x, inter.y)

    coords = list(inter.coords)
    return (coords[0], coords[-1])
```