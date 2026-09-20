```python
from typing import List, Optional, Tuple

from shapely.geometry import Point
from shapely.geometry.polygon import Polygon


def tag_points(
    points: List[Tuple[float, float]], polygons: List[Polygon]
) -> List[Optional[int]]:
    results: List[Optional[int]] = []
    for x, y in points:
        pt = Point(x, y)
        match = None
        for idx, polygon in enumerate(polygons):
            if polygon.covers(pt):
                match = idx
                break
        results.append(match)
    return results
```