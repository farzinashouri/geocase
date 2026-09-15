```python
"""Single-linkage clustering of WGS84 points by geodesic distance."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def _find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent, rank, i, j):
    ri, rj = _find(parent, i), _find(parent, j)
    if ri == rj:
        return
    if rank[ri] < rank[rj]:
        ri, rj = rj, ri
    parent[rj] = ri
    if rank[ri] == rank[rj]:
        rank[ri] += 1


def cluster_points_m(points, max_distance_m):
    n = len(points)
    parent = list(range(n))
    rank = [0] * n

    for i in range(n):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            lon_j, lat_j = points[j]
            _, _, dist = _GEOD.inv(lon_i, lat_i, lon_j, lat_j)
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