```python
"""Single-linkage clustering of WGS84 points by geodesic distance in meters."""

from math import asin, cos, radians, sin, sqrt

_EARTH_RADIUS_M = 6371008.8


def _haversine_m(p, q):
    lon1, lat1 = radians(p[0]), radians(p[1])
    lon2, lat2 = radians(q[0]), radians(q[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * asin(min(1.0, sqrt(a)))


def cluster_points_m(points, max_distance_m):
    """Return cluster labels (0, 1, 2, ... by first appearance) for `points`.

    Two points share a cluster if they are within `max_distance_m` meters of each
    other, directly or via a chain of intermediate points (single linkage).
    """
    n = len(points)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(n):
        for j in range(i + 1, n):
            if _haversine_m(points[i], points[j]) <= max_distance_m:
                union(i, j)

    labels = []
    root_to_label = {}
    for i in range(n):
        r = find(i)
        if r not in root_to_label:
            root_to_label[r] = len(root_to_label)
        labels.append(root_to_label[r])
    return labels
```