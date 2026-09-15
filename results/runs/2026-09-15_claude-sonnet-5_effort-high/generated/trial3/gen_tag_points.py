from typing import List, Optional, Tuple

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


def tag_points(
    points: List[Tuple[float, float]],
    polygons: List[BaseGeometry],
) -> List[Optional[int]]:
    result: List[Optional[int]] = []
    for x, y in points:
        pt = Point(x, y)
        match: Optional[int] = None
        for i, poly in enumerate(polygons):
            if poly.covers(pt):
                match = i
                break
        result.append(match)
    return result