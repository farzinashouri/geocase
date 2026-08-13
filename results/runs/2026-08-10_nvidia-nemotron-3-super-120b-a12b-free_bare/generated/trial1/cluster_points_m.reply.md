```python
from typing import List, Tuple
from pyproj import Geod

def cluster_points_m(points: List[Tuple[float, float]], max_distance_m: float) -> List[int]:
    """
    Cluster geographic points using single-linkage with a distance threshold.

    Parameters
    ----------
    points : list of (lon, lat) tuples in WGS84.
    max_distance_m : distance threshold in meters.

    Returns
    -------
    list of int
        Cluster label for each input point, numbered 0,1,2,... in order of first appearance.
    """
    if not points:
        return []

    # Geodesic calculator for WGS84
    _geod = Geod(ellps='WGS84')

    def _distance_m(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Return geodesic distance between two lon/lat points in meters."""
        lon1, lat1 = p1
        lon2, lat2 = p2
        _, _, dist = _geod.inv(lon1, lat1, lon2, lat2)
        return dist

    n = len(points)
    parent = list(range(n))
    rank = [0] * n

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression (halving)
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            parent[rx] = ry
        elif rank[rx] > rank[ry]:
            parent[ry] = rx
        else:
            parent[ry] = rx
            rank[rx] += 1

    # Single-linkage: union points within max_distance_m
    for i in range(n):
        pi = points[i]
        for j in range(i + 1, n):
            if _distance_m(pi, points[j]) <= max_distance_m:
                union(i, j)

    # Assign cluster labels in order of first appearance
    label_map = {}
    labels = []
    next_label = 0
    for i in range(n):
        root = find(i)
        if root not in label_map:
            label_map[root] = next_label
            next_label += 1
        labels.append(label_map[root])

    return labels
```