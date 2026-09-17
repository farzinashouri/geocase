"""Tag planar points with the index of the polygon that contains them."""

from typing import List, Optional, Sequence, Tuple

from shapely import STRtree
from shapely.geometry import Point, Polygon


def tag_points(
    points: Sequence[Tuple[float, float]],
    polygons: Sequence[Polygon],
) -> List[Optional[int]]:
    """Return, for each point, the index of the polygon containing it.

    A point on a polygon's boundary counts as contained. If a point lies on a
    boundary shared by several polygons, the smallest index is returned. Points
    in no polygon map to ``None``. Output order matches input order.
    """
    result: List[Optional[int]] = [None] * len(points)
    if not points or not polygons:
        return result

    tree = STRtree(list(polygons))
    geoms = [Point(x, y) for x, y in points]

    # "intersects" is inclusive of boundaries, so a point on an edge or vertex
    # matches every polygon that shares that edge or vertex.
    pt_idx, poly_idx = tree.query(geoms, predicate="intersects")

    for i, j in zip(pt_idx.tolist(), poly_idx.tolist()):
        current = result[i]
        if current is None or j < current:
            result[i] = j

    return result