"""Single-linkage clustering of WGS84 points by geodesic distance."""

import numpy as np
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def cluster_points_m(points, max_distance_m):
    """Cluster (lon, lat) points using single-linkage on geodesic distance.

    Two points join the same cluster if they are within `max_distance_m`
    meters of each other, directly or via a chain of intermediate points.

    Returns a list of integer cluster labels, one per input point, numbered
    0, 1, 2, ... in order of first appearance.
    """
    n = len(points)
    if n == 0:
        return []
    if n == 1:
        return [0]

    lons = np.array([p[0] for p in points], dtype=float)
    lats = np.array([p[1] for p in points], dtype=float)

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n - 1):
        rest = n - i - 1
        lon1 = np.full(rest, lons[i])
        lat1 = np.full(rest, lats[i])
        lon2 = lons[i + 1:]
        lat2 = lats[i + 1:]
        _, _, dist = _GEOD.inv(lon1, lat1, lon2, lat2)
        for j in np.where(dist <= max_distance_m)[0]:
            union(i, i + 1 + int(j))

    roots = [find(i) for i in range(n)]
    label_map = {}
    labels = []
    next_label = 0
    for root in roots:
        if root not in label_map:
            label_map[root] = next_label
            next_label += 1
        labels.append(label_map[root])

    return labels