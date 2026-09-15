"""Tag points with the index of the polygon that contains them."""

from typing import List, Optional, Sequence, Tuple

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[BaseGeometry],
) -> List[Optional[int]]:
    tree = STRtree(polygons)
    results: List[Optional[int]] = []
    for x, y in points:
        pt = Point(x, y)
        candidates = tree.query(pt, predicate="covers")
        results.append(int(min(candidates)) if len(candidates) else None)
    return results