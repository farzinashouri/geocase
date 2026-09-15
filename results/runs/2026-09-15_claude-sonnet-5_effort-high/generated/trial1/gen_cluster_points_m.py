"""Cluster geographic points using single-linkage clustering on geodesic distance."""

from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    n = len(points)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for i in range(n):
        lon_i, lat_i = points[i]
        for j in range(i + 1, n):
            lon_j, lat_j = points[j]
            _, _, dist = _GEOD.inv(lon_i, lat_i, lon_j, lat_j)
            if dist <= max_distance_m:
                union(i, j)

    labels = [-1] * n
    next_label = 0
    root_to_label = {}
    for i in range(n):
        root = find(i)
        if root not in root_to_label:
            root_to_label[root] = next_label
            next_label += 1
        labels[i] = root_to_label[root]

    return labels