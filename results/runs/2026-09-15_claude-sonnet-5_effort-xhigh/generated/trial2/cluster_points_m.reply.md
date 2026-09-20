```python
"""Group geographic points into clusters using single-linkage clustering by geodesic distance."""

from pyproj import Geod


class _UnionFind:
    def __init__(self, n):
        self._parent = list(range(n))
        self._rank = [0] * n

    def find(self, x):
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1


def cluster_points_m(points, max_distance_m):
    """Assign single-linkage cluster labels to (lon, lat) points within max_distance_m meters."""
    n = len(points)
    if n == 0:
        return []

    geod = Geod(ellps="WGS84")
    uf = _UnionFind(n)

    for i in range(n):
        lon1, lat1 = points[i]
        for j in range(i + 1, n):
            lon2, lat2 = points[j]
            _, _, distance_m = geod.inv(lon1, lat1, lon2, lat2)
            if distance_m <= max_distance_m:
                uf.union(i, j)

    labels = [-1] * n
    next_label = 0
    root_to_label = {}
    for i in range(n):
        root = uf.find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels[i] = root_to_label[root]

    return labels
```