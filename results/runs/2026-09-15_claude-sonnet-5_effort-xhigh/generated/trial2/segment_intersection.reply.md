```python
"""Segment-segment intersection for 2D line segments."""

from __future__ import annotations

from shapely.geometry import LineString, Point


def segment_intersection(a, b):
    """Return the shared geometry of two 2D segments.

    ``a`` and ``b`` are each ``((x1, y1), (x2, y2))``. Returns ``None`` if the
    segments share no point, a point ``(x, y)`` if they share exactly one
    point, or a segment ``((xa, ya), (xb, yb))`` if they overlap collinearly.
    """
    (ax1, ay1), (ax2, ay2) = a
    (bx1, by1), (bx2, by2) = b

    geom_a = (
        Point(ax1, ay1)
        if (ax1, ay1) == (ax2, ay2)
        else LineString([(ax1, ay1), (ax2, ay2)])
    )
    geom_b = (
        Point(bx1, by1)
        if (bx1, by1) == (bx2, by2)
        else LineString([(bx1, by1), (bx2, by2)])
    )

    inter = geom_a.intersection(geom_b)

    if inter.is_empty:
        return None

    if inter.geom_type == "Point":
        return (inter.x, inter.y)

    coords = list(inter.coords)
    return (coords[0], coords[-1])
```