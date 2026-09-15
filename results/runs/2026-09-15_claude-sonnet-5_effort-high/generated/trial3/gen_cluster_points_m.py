"""Cluster geographic points using single-linkage clustering on geodesic distance."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


class _UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def cluster_points_m(points, max_distance_m):
    """Group points into single-linkage clusters based on a distance threshold.

    Args:
        points: list of (lon, lat) tuples in WGS84 degrees.
        max_distance_m: distance threshold in meters; points within this
            distance (directly or via a chain of intermediate points)
            belong to the same cluster.

    Returns:
        List of integer cluster labels, one per input point, numbered
        0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    uf = _UnionFind(n)

    for i in range(n):
        lon_i, lat_i = points[i]
        if n - i - 1 <= 0:
            continue
        lons_i = [lon_i] * (n - i - 1)
        lats_i = [lat_i] * (n - i - 1)
        lons_j = [points[j][0] for j in range(i + 1, n)]
        lats_j = [points[j][1] for j in range(i + 1, n)]
        _, _, dists = _GEOD.inv(lons_i, lats_i, lons_j, lats_j)
        for offset, dist in enumerate(dists):
            if dist <= max_distance_m:
                uf.union(i, i + 1 + offset)

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