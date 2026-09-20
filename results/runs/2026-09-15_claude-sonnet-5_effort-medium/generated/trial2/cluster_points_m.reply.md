```python
"""Cluster (lon, lat) points by single-linkage using true geodesic distance."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent, rank, a, b):
    ra, rb = _find(parent, a), _find(parent, b)
    if ra == rb:
        return
    if rank[ra] < rank[rb]:
        ra, rb = rb, ra
    parent[rb] = ra
    if rank[ra] == rank[rb]:
        rank[ra] += 1


def cluster_points_m(points, max_distance_m):
    n = len(points)
    parent = list(range(n))
    rank = [0] * n

    for i in range(n):
        lon1, lat1 = points[i]
        for j in range(i + 1, n):
            lon2, lat2 = points[j]
            _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
            if dist <= max_distance_m:
                _union(parent, rank, i, j)

    labels = [-1] * n
    next_label = 0
    label_map = {}
    for i in range(n):
        root = _find(parent, i)
        if root not in label_map:
            label_map[root] = next_label
            next_label += 1
        labels[i] = label_map[root]

    return labels
```